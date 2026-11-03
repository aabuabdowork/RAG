"""Use case for extracting content from documents."""
from pathlib import Path
from typing import Union

from src.domain.entities import ExtractedDocument
from src.domain.interfaces.document_loader import IDocumentLoader


class ExtractDocumentUseCase:
    """Application use case to extract document content through IDocumentLoader abstraction."""

    def __init__(self, loader: IDocumentLoader) -> None:
        self._loader = loader

    def execute(self, file_path: Union[str, Path]) -> ExtractedDocument:
        return self._loader.load(file_path)

