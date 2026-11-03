from typing import List

from src.domain.entities import DocumentEmbedding
from src.domain.interfaces.vector_store import IVectorStore


class IndexDocumentUseCase:
    def __init__(self, store: IVectorStore) -> None:
        self._store = store

    def execute(self, embeddings: List[DocumentEmbedding]) -> int:
        if not embeddings:
            return 0
        self._store.ensure_collection(embeddings[0].dimensions)
        return self._store.upsert(embeddings)
