from typing import List, Optional

from src.domain.entities import SearchMode, SearchResult
from src.domain.exceptions import BudgetExceededError
from src.domain.interfaces.embedding_service import IEmbeddingService
from src.domain.interfaces.vector_store import IVectorStore


class SearchDocumentsUseCase:
    def __init__(self, embedder: IEmbeddingService, store: IVectorStore, max_top_k: int) -> None:
        self._embedder = embedder
        self._store = store
        self._max_top_k = max_top_k

    def execute(
        self,
        query: str,
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> List[SearchResult]:
        if not 1 <= top_k <= self._max_top_k:
            raise BudgetExceededError(f"top_k must be between 1 and {self._max_top_k}, got {top_k}.")

        return self._store.search(
            query=query,
            vector=self._embedder.embed_text(query),
            top_k=top_k,
            min_score=min_score,
            department=department.upper() if department else None,
            mode=mode,
        )
