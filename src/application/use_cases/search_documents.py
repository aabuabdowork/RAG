from typing import List, Optional

from src.domain.entities import SearchResult
from src.domain.interfaces.embedding_service import IEmbeddingService
from src.domain.interfaces.vector_store import IVectorStore


class SearchDocumentsUseCase:
    def __init__(self, embedder: IEmbeddingService, store: IVectorStore) -> None:
        self._embedder = embedder
        self._store = store

    def execute(
        self,
        query: str,
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
    ) -> List[SearchResult]:
        vector = self._embedder.embed_text(query)
        return self._store.search(
            vector,
            top_k=top_k,
            min_score=min_score,
            department=department.upper() if department else None,
        )
