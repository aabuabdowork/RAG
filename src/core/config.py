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
    base_dir: Path = BASE_DIR

    def resolve_doc_path(self, filename: str = "sample.pdf") -> Path:
        for candidate in [self.base_dir / filename, self.base_dir / "doc" / filename]:
            if candidate.exists():
                return candidate
        return self.base_dir / filename


settings = Settings()
