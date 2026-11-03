from abc import ABC, abstractmethod
from typing import List

from src.domain.entities import DocumentEmbedding


class IVectorStore(ABC):
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
