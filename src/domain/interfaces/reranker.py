from abc import ABC, abstractmethod
from typing import List

from src.domain.entities import SearchResult


class IReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, results: List[SearchResult], top_n: int) -> List[SearchResult]:
        pass
