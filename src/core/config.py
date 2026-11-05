"""Configuration management for application."""
import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Suppress deprecation and symlink warnings
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    default_model: str = os.getenv("DEFAULT_MODEL", "openai/gpt-oss-20b")
    default_embedding_model: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "langchain_rag")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    min_score: float = float(os.getenv("MIN_SCORE", "0.3"))
    search_mode: str = os.getenv("SEARCH_MODE", "hybrid")
    prefetch_limit: int = int(os.getenv("PREFETCH_LIMIT", "20"))
    token_encoding: str = os.getenv("TOKEN_ENCODING", "o200k_base")
    max_question_tokens: int = int(os.getenv("MAX_QUESTION_TOKENS", "200"))
    max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "1500"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "500"))
    max_top_k: int = int(os.getenv("MAX_TOP_K", "10"))
    rerank_enabled: bool = os.getenv("RERANK_ENABLED", "true").lower() == "true"
    rerank_model: str = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    rerank_candidates: int = int(os.getenv("RERANK_CANDIDATES", "20"))
    min_rerank_score: float = float(os.getenv("MIN_RERANK_SCORE", "0.0"))
    multi_query_enabled: bool = os.getenv("MULTI_QUERY_ENABLED", "false").lower() == "true"
    max_query_variants: int = int(os.getenv("MAX_QUERY_VARIANTS", "3"))
    multi_query_candidates: int = int(os.getenv("MULTI_QUERY_CANDIDATES", "10"))
    base_dir: Path = BASE_DIR
    docs_dir: Path = Path(os.getenv("DOCS_DIR", BASE_DIR / "departments"))

    def resolve_doc_path(self, filename: str = "sample.pdf") -> Path:
        for candidate in [self.base_dir / filename, self.base_dir / "doc" / filename]:
            if candidate.exists():
                return candidate
        return self.base_dir / filename


settings = Settings()
