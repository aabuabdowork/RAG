from abc import ABC, abstractmethod
from typing import List

from src.domain.entities import DocumentEmbedding


class IVectorStore(ABC):
    @abstractmethod
    def ensure_collection(self, dimension: int) -> None:
        pass

    @abstractmethod
    def upsert(self, embeddings: List[DocumentEmbedding]) -> int:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
