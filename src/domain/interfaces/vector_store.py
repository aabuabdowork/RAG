from abc import ABC, abstractmethod
from typing import List

from src.domain.entities import DocumentEmbedding, SearchResult


class IVectorStore(ABC):
    @abstractmethod
    def search(self, vector: List[float], top_k: int, min_score: float) -> List[SearchResult]:
        pass

    @abstractmethod
    def exists(self, doc_hash: str) -> bool:
        pass

    @abstractmethod
    def delete_by_file(self, file_name: str) -> int:
        pass

    @abstractmethod
    def upsert(self, embeddings: List[DocumentEmbedding]) -> int:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
