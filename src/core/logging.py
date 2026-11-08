import logging

from src.core.config import settings

LOG_FILE = settings.log_dir / "app.log"


def setup_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
