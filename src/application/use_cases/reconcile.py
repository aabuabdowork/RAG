from dataclasses import replace
from typing import Dict

from src.domain.entities import Document, DocumentStatus
from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.vector_store import IVectorStore


class ReconcileUseCase:
    def __init__(self, repository: IDocumentRepository, store: IVectorStore) -> None:
        self._repository = repository
        self._store = store

    def execute(self) -> Dict[str, str]:
        documents = self._repository.list()
        counts = self._store.count_by_document()
        results: Dict[str, str] = {}

        for document in documents:
            if self._is_out_of_sync(document, counts.get(document.id, 0)):
                self._repository.save(replace(document, status=DocumentStatus.PENDING))
                results[document.key] = "requeued"

        for orphan_id in counts.keys() - {document.id for document in documents}:
            self._store.delete_document(orphan_id)
            results[orphan_id] = "orphan removed"
        return results

    @staticmethod
    def _is_out_of_sync(document: Document, points: int) -> bool:
        if document.status == DocumentStatus.PROCESSING:
            return True
        return document.status == DocumentStatus.INDEXED and points != document.chunk_count
