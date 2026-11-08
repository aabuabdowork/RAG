import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Dict, List

from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.domain.entities import Document, DocumentEmbedding, DocumentStatus
from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.object_storage import IObjectStorage
from src.domain.interfaces.vector_store import IVectorStore


class IndexDocumentsUseCase:
    def __init__(
        self,
        repository: IDocumentRepository,
        storage: IObjectStorage,
        embed: EmbedDocumentUseCase,
        store: IVectorStore,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._embed = embed
        self._store = store

    def execute(self) -> Dict[str, str]:
        return {
            document.key: self._index(document)
            for document in self._repository.list(DocumentStatus.PENDING)
        }

    def _index(self, document: Document) -> str:
        self._repository.save(replace(document, status=DocumentStatus.PROCESSING))
        try:
            embeddings = self._embeddings(document)
            if not embeddings:
                raise ValueError("no text extracted")
            self._store.delete_document(document.id)
            self._store.upsert(embeddings)
        except Exception as error:
            self._repository.save(replace(document, status=DocumentStatus.FAILED, error=str(error)))
            return f"failed ({error})"

        self._repository.save(
            replace(document, status=DocumentStatus.INDEXED, chunk_count=len(embeddings), error=None)
        )
        return "indexed"

    def _embeddings(self, document: Document) -> List[DocumentEmbedding]:
        metadata = {
            "document_id": document.id,
            "doc_hash": document.doc_hash,
            "department": document.department,
            "file_name": document.file_name,
            "source": document.storage_path,
        }
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            path = Path(folder) / document.file_name
            path.write_bytes(self._storage.download(document.storage_path))
            return [
                replace(emb, metadata={**emb.metadata, **metadata})
                for emb in self._embed.execute(path)
            ]
