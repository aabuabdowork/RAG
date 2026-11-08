import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.core.config import settings
from src.core.request_context import request_id
from src.domain.interfaces.metrics import IMetrics


class JsonlMetrics(IMetrics):
    def __init__(self, path: Path = settings.log_dir / "metrics.jsonl") -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(self, event: str, **fields: Any) -> None:
        line = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "request_id": request_id.get(),
            "event": event,
            **fields,
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(line) + "\n")

    def events(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock, self.path.open(encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]
