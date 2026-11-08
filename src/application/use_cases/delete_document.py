from src.domain.interfaces.document_repository import IDocumentRepository
from src.domain.interfaces.object_storage import IObjectStorage
from src.domain.interfaces.vector_store import IVectorStore


class DeleteDocumentUseCase:
    def __init__(self, repository: IDocumentRepository, storage: IObjectStorage, store: IVectorStore) -> None:
        self._repository = repository
        self._storage = storage
        self._store = store

    def execute(self, department: str, file_name: str) -> str:
        document = self._repository.get(department.upper(), file_name)
        if not document:
            return "not found"

        points = self._store.delete_document(document.id)
        self._storage.delete(document.storage_path)
        self._repository.delete(document.id)
        return f"deleted ({points} points)"
