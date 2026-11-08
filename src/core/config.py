"""Configuration management for application."""
import os
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

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
    fallback_model: str = os.getenv("FALLBACK_MODEL", "openai/gpt-oss-120b")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "30"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    default_embedding_model: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "langchain_rag")
    qdrant_timeout: int = int(os.getenv("QDRANT_TIMEOUT", "10"))
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
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_hours: float = float(os.getenv("CACHE_TTL_HOURS", "24"))
    api_keys: Tuple[str, ...] = tuple(key.strip() for key in os.getenv("API_KEYS", "").split(",") if key.strip())
    departments: Tuple[str, ...] = tuple(
        name.strip().upper() for name in os.getenv("DEPARTMENTS", "HR,IT").split(",") if name.strip()
    )
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    rate_limit_storage: str = os.getenv("RATE_LIMIT_STORAGE", "memory://")
    rate_limit_ask: str = os.getenv("RATE_LIMIT_ASK", "10/minute")
    rate_limit_search: str = os.getenv("RATE_LIMIT_SEARCH", "30/minute")
    rate_limit_read: str = os.getenv("RATE_LIMIT_READ", "30/minute")
    rate_limit_write: str = os.getenv("RATE_LIMIT_WRITE", "5/minute")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_bucket: str = os.getenv("SUPABASE_BUCKET", "documents")
    supabase_table: str = os.getenv("SUPABASE_TABLE", "documents")
    base_dir: Path = BASE_DIR
    docs_dir: Path = Path(os.getenv("DOCS_DIR", BASE_DIR / "departments"))
    log_dir: Path = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", BASE_DIR / ".cache"))
    eval_dataset: Path = Path(os.getenv("EVAL_DATASET", BASE_DIR / "evaluation" / "dataset.json"))

    def resolve_doc_path(self, filename: str = "sample.pdf") -> Path:
        for candidate in [self.base_dir / filename, self.base_dir / "doc" / filename]:
            if candidate.exists():
                return candidate
        return self.base_dir / filename


settings = Settings()
