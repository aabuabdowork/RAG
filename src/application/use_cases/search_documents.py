from typing import Dict, List, Optional, Tuple

from src.application.use_cases.expand_query import ExpandQueryUseCase
from src.domain.entities import Retrieval, SearchMode, SearchResult
from src.domain.exceptions import BudgetExceededError
from src.domain.interfaces.embedding_service import IEmbeddingService
from src.domain.interfaces.reranker import IReranker
from src.domain.interfaces.vector_store import IVectorStore


class SearchDocumentsUseCase:
    def __init__(
        self,
        embedder: IEmbeddingService,
        store: IVectorStore,
        max_top_k: int,
        reranker: Optional[IReranker] = None,
        expander: Optional[ExpandQueryUseCase] = None,
        rerank_candidates: int = 20,
        multi_query_candidates: int = 10,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._max_top_k = max_top_k
        self._reranker = reranker
        self._expander = expander
        self._rerank_candidates = rerank_candidates
        self._multi_query_candidates = multi_query_candidates

    def execute(
        self,
        query: str,
        top_k: int,
        min_score: float,
        department: Optional[str] = None,
        mode: SearchMode = SearchMode.HYBRID,
    ) -> Retrieval:
        if not 1 <= top_k <= self._max_top_k:
            raise BudgetExceededError(f"top_k must be between 1 and {self._max_top_k}, got {top_k}.")

        queries = [query] + (self._expander.execute(query) if self._expander else [])
        limit = self._candidate_limit(top_k, len(queries))
        department = department.upper() if department else None

        found: Dict[Tuple[str, str, int, int], SearchResult] = {}
        for text in queries:
            for result in self._store.search(
                query=text,
                vector=self._embedder.embed_text(text),
                top_k=limit,
                min_score=min_score,
                department=department,
                mode=mode,
            ):
                key = (result.department, result.file_name, result.page_number, result.chunk_index)
                if key not in found or result.score > found[key].score:
                    found[key] = result

        candidates = sorted(found.values(), key=lambda result: result.score, reverse=True)
        results = self._reranker.rerank(query, candidates, top_k) if self._reranker else candidates[:top_k]
        return Retrieval(queries=queries, results=results)

    def _candidate_limit(self, top_k: int, query_count: int) -> int:
        if not self._reranker:
            return top_k
        per_query = self._multi_query_candidates if query_count > 1 else self._rerank_candidates
        return max(top_k, per_query)
