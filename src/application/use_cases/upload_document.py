import hashlib
import uuid
from pathlib import Path

from src.domain.entities import Document, DocumentStatus
from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.object_storage import IObjectStorage


def document_id(department: str, file_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{department.upper()}/{file_name}"))


class UploadDocumentUseCase:
    def __init__(self, repository: IDocumentRepository, storage: IObjectStorage) -> None:
        self._repository = repository
        self._storage = storage

    def execute(self, file_name: str, data: bytes, department: str) -> str:
        department = department.upper()
        doc_hash = hashlib.sha256(data).hexdigest()

        existing = self._repository.get(department, file_name)
        if existing and existing.doc_hash == doc_hash and existing.status != DocumentStatus.FAILED:
            return "skipped"

        identifier = document_id(department, file_name)
        document = Document(
            id=identifier,
            department=department,
            file_name=file_name,
            storage_path=f"{department}/{identifier}{Path(file_name).suffix.lower()}",
            doc_hash=doc_hash,
        )
        self._storage.upload(document.storage_path, data)
        self._repository.save(document)
        return "updated" if existing else "uploaded"
