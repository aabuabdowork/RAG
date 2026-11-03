"""Interface contract for document loaders."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from src.domain.entities import ExtractedDocument


class IDocumentLoader(ABC):
    """Abstract interface for extracting text from document files."""

    @abstractmethod
    def load(self, file_path: Union[str, Path]) -> ExtractedDocument:
        """Load and extract text from the specified file path."""
        pass

