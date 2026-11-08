from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities import Document, DocumentStatus


class IDocumentRepository(ABC):
    @abstractmethod
    def get(self, department: str, file_name: str) -> Optional[Document]:
        pass

    @abstractmethod
    def list(self, status: Optional[DocumentStatus] = None) -> List[Document]:
        pass

    @abstractmethod
    def save(self, document: Document) -> None:
        pass

    @abstractmethod
    def delete(self, document_id: str) -> None:
        pass
