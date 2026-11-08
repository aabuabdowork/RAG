import hashlib
import json
from typing import Optional

from src.domain.interfaces.cache import ICache
from src.domain.interfaces.llm_service import ILLMService
from src.domain.interfaces.metrics import IMetrics


class CachedLLMService(ILLMService):
    def __init__(self, llm: ILLMService, cache: ICache, namespace: str, metrics: Optional[IMetrics] = None) -> None:
        self._llm = llm
        self._cache = cache
        self._namespace = namespace
        self._metrics = metrics

    def generate(self, prompt: str, system: str = "", name: str = "llm") -> str:
        key = hashlib.sha256(json.dumps([self._namespace, system, prompt]).encode()).hexdigest()
        cached = self._cache.get(key)
        if self._metrics:
            self._metrics.record("cache", name=name, hit=cached is not None)
        if cached is not None:
            return cached

        text = self._llm.generate(prompt, system=system, name=name)
        if text.strip():
            self._cache.set(key, text)
        return text
