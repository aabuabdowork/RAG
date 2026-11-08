import hashlib
import uuid
from pathlib import Path
from typing import Union

from src.domain.entities import Document, DocumentStatus
from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.object_storage import IObjectStorage


class UploadDocumentUseCase:
    def __init__(self, repository: IDocumentRepository, storage: IObjectStorage) -> None:
        self._repository = repository
        self._storage = storage

    def execute(self, file_path: Union[str, Path], department: str) -> str:
        path = Path(file_path)
        department = department.upper()
        data = path.read_bytes()
        doc_hash = hashlib.sha256(data).hexdigest()

        existing = self._repository.get(department, path.name)
        if existing and existing.doc_hash == doc_hash and existing.status != DocumentStatus.FAILED:
            return "skipped"

        document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{department}/{path.name}"))
        document = Document(
            id=document_id,
            department=department,
            file_name=path.name,
            storage_path=f"{department}/{document_id}{path.suffix.lower()}",
            doc_hash=doc_hash,
        )
        self._storage.upload(document.storage_path, data)
        self._repository.save(document)
        return "updated" if existing else "uploaded"
