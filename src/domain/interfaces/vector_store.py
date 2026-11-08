from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.entities import DocumentEmbedding, SearchMode, SearchResult


class IVectorStore(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        vector: List[float],
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> List[SearchResult]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> int:
        pass

    @abstractmethod
    def count_by_document(self) -> Dict[str, int]:
        pass

    @abstractmethod
    def upsert(self, embeddings: List[DocumentEmbedding]) -> int:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
