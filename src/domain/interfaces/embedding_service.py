"""Interface contract for embedding services."""
from abc import ABC, abstractmethod
from typing import List


class IEmbeddingService(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Convert a single text string into a vector embedding."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple text strings into vector embeddings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        pass

