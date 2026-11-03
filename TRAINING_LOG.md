# LangChain RAG — Training Log

A step-by-step record of what we built, why, and what we learned.

---

## Project Overview

A document pipeline built with **clean architecture**:

```
doc/*.pdf ──► Hash check ──► Extract ──► Chunk ──► Embed ──► Index (Qdrant)
```

| Layer | Folder | Role |
|---|---|---|
| Domain | `src/domain` | Entities + interfaces (contracts). No external libraries. |
| Application | `src/application/use_cases` | Use cases: extract, embed, ingest (document/folder), analyze. |
| Infrastructure | `src/infrastructure` | Adapters: PyPDF, HuggingFace, Qdrant, OpenRouter, splitter. |
| Core | `src/core` | Settings / `.env` config. |
| Composition Root | `main.py` | Wires everything together and runs it. |

**Run:** `docker compose up -d` → `python main.py`

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

- [ ] Retrieval: embed a user question → search Qdrant → top-k chunks.
- [ ] RAG answer: send retrieved chunks + question to the LLM.
- [ ] Arabic documents → switch to a multilingual embedding model (MiniLM is English-only).
- [x] Re-indexing an edited document leaves old chunks behind → solved in Step 6 (delete by `file_name`).
- [ ] Sync deletions: remove points for files no longer in `doc/`.
- [ ] Upload API (FastAPI): `POST /documents`, `GET /documents/{id}`, background processing, `documents` registry table (status: pending → processing → done/failed).
