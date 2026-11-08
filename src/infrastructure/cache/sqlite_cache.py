import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from src.core.config import settings
from src.domain.interfaces.cache import ICache


class SqliteCache(ICache):
    def __init__(
        self,
        path: Path = settings.cache_dir / "llm_cache.db",
        ttl_hours: float = settings.cache_ttl_hours,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            "create table if not exists cache (key text primary key, value text not null, created_at real not null)"
        )
        self._ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            row = self._connection.execute(
                "select value from cache where key = ? and created_at > ?",
                (key, time.time() - self._ttl_seconds),
            ).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "insert or replace into cache values (?, ?, ?)", (key, value, time.time())
            )
