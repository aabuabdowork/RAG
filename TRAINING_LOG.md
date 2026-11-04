# LangChain RAG — Training Log

A step-by-step record of what we built, why, and what we learned.

---

## Project Overview

A document pipeline built with **clean architecture**:

```
departments/<DEPT>/*.pdf ──► Hash check ──► Extract ──► Chunk ──► Embed ──► Index (Qdrant)
question ──► Hybrid search (dense + BM25 → RRF, optional department filter) ──► top-k chunks ──► LLM ──► answer + sources
```

| Layer | Folder | Role |
|---|---|---|
| Domain | `src/domain` | Entities + interfaces (contracts). No external libraries. |
| Application | `src/application/use_cases` | Use cases: extract, embed, ingest (document/folder), analyze. |
| Infrastructure | `src/infrastructure` | Adapters: PyPDF, HuggingFace, Qdrant, OpenRouter, splitter. |
| Core | `src/core` | Settings / `.env` config. |
| Composition Root | `main.py` | Wires everything together and runs it. |

**Run:** `docker compose up -d` → `python main.py ingest` → `python main.py search "your question"`

---

## Step 1 — Git Setup (2026-11-03)

**What:** Initialized git repo on `main`, expanded `.gitignore`, first commit `6f9789f`.

**Why:** Track every change so we can review and roll back.

**Key points**
- `.env` is ignored → API keys never get committed.
- Also ignored: `__pycache__/`, virtual envs, IDE/OS files, model/vector caches.

---

## Step 2 — Vector Database Choice (2026-11-03)

**What:** Chose **Qdrant** over Elasticsearch to store embeddings.

| | Elasticsearch | Qdrant |
|---|---|---|
| RAM | Heavy (~1–2 GB) | Light (~100–200 MB) |
| Purpose | Search engine + vectors | Vector-only DB |
| Hybrid (keyword + vector) | Strong | Possible |
| Fit for learning RAG | OK | Best |

**Setup:** `docker-compose.yml` → container `langchain-rag-system`, image `qdrant/qdrant:v1.20.0`.

| Item | Value |
|---|---|
| REST API | `http://localhost:6333` |
| Dashboard | `http://localhost:6333/dashboard` |
| gRPC | `6334` |
| Data volume | `langchain-rag-system_data` (survives restarts) |

**Commands**
```bash
docker compose up -d     # start
docker compose down      # stop
```

---

## Step 3 — Store Embeddings in Qdrant (2026-11-03)

**What:** Added an indexing step that saves each embedding + its text + metadata into Qdrant.

**Files**
- `src/domain/interfaces/vector_store.py` — `IVectorStore` contract
- `src/infrastructure/vectorstores/qdrant_store.py` — Qdrant adapter
- `src/application/use_cases/index_document.py` — `IndexDocumentUseCase`
- `src/core/config.py` — `QDRANT_URL`, `QDRANT_COLLECTION` (`langchain_rag`)

**Key points**
- Collection is auto-created with vector size **384** and **Cosine** distance.
- A Qdrant record is called a **point** = `id` + `vector` + `payload` (text + metadata).
- Point IDs are **deterministic** (`uuid5` of source + page + chunk) → re-running updates, never duplicates.

**Where to see it in the dashboard**
- Collections → `langchain_rag` → **Info** tab → vector size (dimensions)
- **Points** tab → payload + vector values
- **Visualize** tab → 2D map of vectors
- Console:
  ```
  POST collections/langchain_rag/points/scroll
  { "limit": 10, "with_payload": true, "with_vector": true }
  ```

---

## Step 4 — Recursive Chunking (2026-11-03)

**What:** Split each page into small chunks before embedding, using LangChain's `RecursiveCharacterTextSplitter`.

**Files**
- `src/domain/interfaces/text_splitter.py` — `ITextSplitter` contract
- `src/infrastructure/splitters/recursive_splitter.py` — recursive adapter
- `src/application/use_cases/embed_document.py` — now splits → embeds per chunk
- `src/core/config.py` — `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`

**Why chunk at all?**
- `all-MiniLM-L6-v2` reads max **256 tokens** → the rest of a long page is silently dropped.
- One vector per page mixes many topics → blurry search results.
- Smaller retrieved text → fewer tokens sent to the LLM.

**Chunking strategies**
| Strategy | How it splits | Notes |
|---|---|---|
| Fixed | Every N characters | Simple, cuts words/sentences |
| **Recursive** ✅ | `\n\n` → `\n` → space → char | Respects natural boundaries; standard default |
| Semantic | Where meaning changes | Smarter, slower |
| Document-based | Markdown headers / HTML tags | Structured docs |
| Token-based | Counts tokens, not chars | Precise model limits |

**Why 800 / 100?**
- 256 tokens × ~4 chars/token ≈ 1,000 chars max → **800** leaves a safety margin (≈200 tokens).
- 800 chars ≈ one paragraph ≈ one idea → sharper vector.
- **100** overlap ≈ one sentence (~12%, rule of thumb 10–20%) → ideas cut at a boundary survive in the next chunk.
- These are starting values — tune by testing retrieval on real documents.

**Verified:** 2,978-char test text → 5 chunks of ~593 chars.

**Each Qdrant point payload now includes:** `text`, `source`, `page_number`, `chunk_index`.

---

## Step 5 — Hide `__pycache__` in VS Code (2026-11-03)

**What:** Added `.vscode/settings.json` with `files.exclude` for `**/__pycache__` and `**/*.pyc`.

**Why:** `__pycache__` holds compiled bytecode (`.pyc`) that Python auto-creates for faster startup. Useful, but visual noise.

**Key points**
- Folders still exist on disk; VS Code just hides them.
- Safe to delete anytime; Python recreates them.
- Already ignored by git.

---

## Step 6 — Folder Ingestion + Duplicate Detection (2026-11-03)

**What:** `python main.py` now ingests **every PDF in `doc/`** and skips anything already indexed.

**Flow per file**
```
hash = sha256(file bytes)
same hash in Qdrant?              → skipped
same file name, different hash?   → delete old points → re-index → updated
otherwise                         → indexed
no text extracted                 → empty
error                             → failed (reason), other files continue
```

**Files**
- `src/application/use_cases/ingest_document.py` — one file → status (the core; upload will reuse it)
- `src/application/use_cases/ingest_folder.py` — loops `doc/*.pdf`, calls the above
- `src/domain/interfaces/vector_store.py` — added `exists(doc_hash)`, `delete_by_file(file_name)`
- `src/infrastructure/vectorstores/qdrant_store.py` — collection created on start, keyword indexes on `doc_hash` + `file_name`
- `src/core/config.py` — `DOCS_DIR` (default `doc/`)
- `main.py` — wires ingestion, prints per-file status + summary
- Removed `index_document.py` (replaced by ingest)

**Why content hash, not file name/path**
| Check by | Problem |
|---|---|
| File name | Rename → duplicate; edit with same name → wrongly skipped |
| Path | Move → duplicate |
| **SHA-256 of content** ✅ | Same content = same hash, regardless of name/location |

**Key points**
- Hash check happens **before** extract/embed → no wasted compute.
- Point ID = `uuid5(doc_hash + page + chunk)` → same content always maps to same IDs.
- **Payload index** = like a DB index; makes filtering by `doc_hash` fast.

**Verified**
| Run | Scenario | Result |
|---|---|---|
| 1 | Fresh | `indexed` |
| 2 | Re-run | `skipped` |
| 3 | Copy with new name | `skipped` (same hash) |
| 4–6 | Same name, edited content | `updated`, point count unchanged (no duplicates) |

**Known limits**
- Two different files with the **same name** in different folders would replace each other (fine for one flat `doc/` folder).
- Renamed file is skipped, but payload keeps the old `file_name`.
- Deleting a file from `doc/` does not remove its points yet.

---

## Step 7 — Second Sample Document (2026-11-03)

**What:** Added `doc/remote_work_policy.pdf`, a fictional 3-page HR policy (Falcon Tech), generated with `reportlab`.

**Why:** A realistic, fact-rich document to test chunking now and RAG questions later.

**Result:** each page is ~820–960 chars → **2 chunks per page** → 6 points (+1 from `sample.pdf` = 7 total). `sample.pdf` was `skipped`.

**Good test questions for the retrieval step**
- How many remote days per week are allowed?
- What are the core hours?
- How much is the home office allowance?
- Where do I report a data leak?

---

## Step 8 — Search with Scores (2026-11-03)

**What:** Semantic search over Qdrant. A question is embedded with the **same** MiniLM model and compared to all chunks.

**Commands**
```bash
python main.py ingest
python main.py search "How many remote days per week are allowed?"
python main.py search "core hours" --top-k 5 --min-score 0.4
```

**Files**
- `src/domain/entities.py` — `SearchResult` (text, score, file_name, page_number, chunk_index)
- `src/domain/interfaces/vector_store.py` — `search(vector, top_k, min_score)`
- `src/infrastructure/vectorstores/qdrant_store.py` — uses Qdrant `query_points` with `score_threshold`
- `src/application/use_cases/search_documents.py` — `SearchDocumentsUseCase`
- `src/core/config.py` — `TOP_K=3`, `MIN_SCORE=0.3`
- `main.py` — `ingest` / `search` commands (argparse)

**Score concepts**
| Term | Meaning |
|---|---|
| Score | Cosine similarity, −1 → 1. Higher = closer meaning. |
| top_k | Max number of chunks returned. |
| min_score | Threshold; below it a chunk is ignored → "No relevant results". |

**Calibration (MiniLM, our documents)**
| Question | Best score | Correct chunk? |
|---|---|---|
| How many remote days per week? | 0.604 / 0.524 | Yes, in top 2 |
| What are the core hours? | 0.580 | Yes |
| Home office allowance? | 0.403 | Yes |
| Report a data leak? | 0.505 | Yes |
| Capital of France? (off-topic) | 0.012 | — |
| Bake a chocolate cake? (off-topic) | < 0 | — |

→ Relevant ≈ **0.40–0.60**, unrelated ≈ **≤ 0.21** → `MIN_SCORE=0.3` sits in the gap.

**Lessons**
- Scores are **relative to the model**: re-calibrate if the embedding model changes.
- The best answer is not always rank 1 ("remote days" answer was rank 2) → send top_k chunks to the LLM, not just one.
- A threshold lets the system say "not found" instead of hallucinating.

---

## Step 9 — Departments + Metadata Filter (2026-11-04)

**What:** Documents are organized by department; search can be limited to one department.

**New folder layout** (replaces `doc/`)
```
departments/
├── HR/remote_work_policy.pdf
└── IT/sample.pdf
```
The **sub-folder name = department**. A new department = a new folder, no code change.

**Commands**
```bash
python main.py ingest
python main.py search "core hours"                    # all departments
python main.py search "core hours" --department HR    # HR only
python main.py search "core hours" --department it    # case-insensitive → IT only
```

**Changes**
- `ingest_folder.py` — loops each department folder, passes `department` to ingest
- `ingest_document.py` — adds `department` (upper-case) + `file_path` (`HR/remote_work_policy.pdf`) to payload
- `vector_store.py` / `qdrant_store.py` — `search(..., department)` uses a Qdrant `query_filter`; keyword indexes on `doc_hash`, `file_path`, `department`
- `delete_by_file` now uses `file_path` → same file name in two departments no longer collides
- `search_documents.py`, `main.py` — `--department` option
- `config.py` — `DOCS_DIR` default `departments/`
- Deleted the old collection and re-indexed from scratch (new payload schema)

**Verified**
| Query | Filter | Result |
|---|---|---|
| core hours | none | 3 HR chunks (best 0.556) |
| core hours | HR | same 3 HR chunks |
| core hours | IT | No relevant results |
| PDF text extraction | IT | `IT/sample.pdf` (0.783) |

**Key concepts**
- **Metadata filter** = "search only where `department == HR`", applied *during* the vector search (pre-filter), not after.
- **Payload index** on `department` keeps filtered search fast as data grows.
- This is the basis for **access control**: later, a user's department decides which filter is applied.

**Known limit:** the same PDF in two departments is indexed only once (global hash check) → it only appears under the first department.

---

## Step 10 — RAG Answer with LLM (2026-11-04)

**What:** The full RAG loop. Retrieved chunks are given to the LLM, which answers **only** from them and cites sources.

```
question ──► search (top_k, min_score, department) ──► chunks
        ──► prompt (rules + chunks + question) ──► LLM (OpenRouter gpt-oss-20b) ──► answer + sources
```

**Command**
```bash
python main.py ask "How many remote days per week are allowed?" --department HR
```

**Files**
- `src/domain/entities.py` — `Answer` (text, sources)
- `src/application/use_cases/ask_question.py` — `AskQuestionUseCase` (prompt template + context builder)
- `main.py` — new `ask` command; `search`/`ask` share options (`--top-k`, `--min-score`, `--department`)
- Reuses existing `OpenRouterLLMService` and `SearchDocumentsUseCase` — no new libraries

**Prompt rules (grounding)**
1. Use only facts from the context, no outside knowledge.
2. Cite each fact as `[DEPT/file.pdf, p.N]`.
3. If the answer is not in the context → reply exactly "I couldn't find this in the documents."

**Two safety layers against hallucination**
| Layer | When | Cost |
|---|---|---|
| `min_score` threshold | No chunk relevant enough → return "not found" **without calling the LLM** | Free |
| Prompt rule | Chunks found but don't contain the answer → LLM says "not found" | 1 LLM call |

**Verified**
| Question | Filter | Result |
|---|---|---|
| Remote days per week? | HR | "three days… fourth day for special cases" + citation ✅ |
| Home office allowance + how to claim? | all | "1,500 SAR, receipts within 30 days" + citation ✅ |
| Parental leave policy? | all | Chunk retrieved (0.441) but LLM said "not found" ✅ (layer 2) |
| Bake a chocolate cake? | all | "not found", no LLM call ✅ (layer 1) |
| Core hours? | IT | "not found" (HR content filtered out) ✅ |

**Lessons**
- **Retrieval ≠ relevance:** a chunk can score above the threshold and still not contain the answer → the prompt rule is essential.
- Answers can combine facts from several chunks → send top_k chunks, not just #1.
- The department filter also controls what the LLM can "see" → basis for access control.

---

## Step 11 — Hybrid Search: Dense + BM25 + RRF (2026-11-04)

**What:** Search now combines **semantic** (MiniLM dense vectors) and **keyword** (BM25 sparse vectors) results, merged with **Reciprocal Rank Fusion (RRF)**.

```
                    ┌─► dense  (MiniLM, cosine, min_score)  top 20 ─┐
question ──► embed ─┤                                               ├─► RRF ──► top_k ──► LLM
                    └─► sparse (BM25, IDF)                  top 20 ─┘
                    (department filter applied to both)
```

**How BM25 is computed:** by **Qdrant itself** (built-in `qdrant/bm25` inference, server ≥ 1.15) — we send raw text, Qdrant tokenizes, stems, and weights it. No new Python library.

**Commands**
```bash
python main.py search "VPN"                       # hybrid (default)
python main.py search "VPN" --mode dense          # semantic only
python main.py search "VPN" --mode sparse         # BM25 only
python main.py ask "What is the policy version?"  # RAG uses hybrid
```

**Changes**
- `entities.py` — `SearchMode` enum (`hybrid`, `dense`, `sparse`)
- `qdrant_store.py` — named vectors `dense` + sparse `bm25` (`Modifier.IDF`); hybrid = 2 `Prefetch` + `FusionQuery(RRF)`; client uses `cloud_inference=True` so text is embedded server-side
- `vector_store.py`, `search_documents.py`, `ask_question.py` — pass `query` text + `mode`
- `config.py` — `SEARCH_MODE=hybrid`, `PREFETCH_LIMIT=20`
- `main.py` — `--mode` option on `search` and `ask`
- Collection deleted and re-indexed (new vector layout)

**Comparison (top 3, min_score 0.3)**
| Query | Dense | Sparse (BM25) | Hybrid |
|---|---|---|---|
| `VPN` | ❌ no results | ✅ | ✅ |
| `security@falcontech.example` | ⚠️ answer at rank 3 | ✅ rank 1 | ✅ rank 1 |
| `version 2.1` | ❌ no results | ✅ | ✅ |
| `1,500 SAR` | ❌ no results | ✅ | ✅ |
| `work from home` | ✅ (1 result) | ⚠️ rank 1 wrong ("home office") | ✅ rank 1 |
| `laptop rules` | ✅ | ✅ | ✅ |
| `bake a chocolate cake` | none ✅ | none ✅ | none ✅ |

→ Dense fails on **exact terms**, BM25 fails on **meaning**; hybrid gets **both**.

**Scores per mode (important!)**
| Mode | Score type | Range | `min_score` applies? |
|---|---|---|---|
| dense | Cosine similarity | −1 → 1 | ✅ |
| sparse | BM25 relevance | 0 → unbounded (e.g. 5.9) | ❌ |
| hybrid | RRF (rank-based) | 0 → 1 (1.0 = rank 1 in both lists) | ✅ on the dense side only |

**Key concepts**
| Term | Meaning |
|---|---|
| **Dense vector** | Every dimension has a value (384 floats); captures meaning. |
| **Sparse vector** | Mostly zeros; only words present in the text have a weight. |
| **BM25** | Classic keyword ranking: rare words that appear often in a chunk score high. |
| **IDF** | Inverse Document Frequency — rare words matter more; Qdrant computes it over the whole collection. |
| **Prefetch** | Sub-query that collects candidates before fusion. |
| **RRF** | Merges ranked lists by position: score = Σ 1/(k + rank). Ignores raw score scales. |

---

## Glossary

| Term | Meaning |
|---|---|
| **Embedding** | Text converted to a list of numbers (vector) that captures meaning. |
| **Dimensions** | Length of the vector (MiniLM = 384). |
| **Vector DB** | Database that stores vectors and finds the most similar ones. |
| **Collection** | A "table" in Qdrant. |
| **Point** | One record in Qdrant: id + vector + payload. |
| **Payload** | Extra JSON data stored with a vector (text, metadata). |
| **Cosine distance** | Similarity measure based on the angle between vectors. |
| **Chunk** | A small piece of a document, embedded separately. |
| **Chunk overlap** | Characters shared between neighboring chunks. |
| **Upsert** | Insert if new, update if the ID already exists. |
| **RAG** | Retrieval-Augmented Generation: retrieve relevant chunks, then give them to the LLM. |

---

## Open Notes / Next Steps

- [x] Retrieval: embed a user question → search Qdrant → top-k chunks (Step 8).
- [x] RAG answer: send retrieved chunks + question to the LLM (Step 10).
- [ ] Arabic documents → switch to a multilingual embedding model (MiniLM is English-only).
- [x] Re-indexing an edited document leaves old chunks behind → solved in Step 6 (delete by `file_name`).
- [ ] Sync deletions: remove points for files no longer in `doc/`.
- [ ] Upload API (FastAPI): `POST /documents`, `GET /documents/{id}`, background processing, `documents` registry table (status: pending → processing → done/failed).
