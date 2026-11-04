"""Domain entities representing core business models."""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class DocumentPage:
    """Represents a single page extracted from a document."""
    page_number: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedDocument:
    """Represents a fully extracted document consisting of pages."""
    source_path: str
    pages: List[DocumentPage]

    @property
    def full_text(self) -> str:
        """Concatenate all pages text."""
        return "\n\n".join(page.content for page in self.pages)

    @property
    def total_pages(self) -> int:
        return len(self.pages)


@dataclass(frozen=True)
class SearchResult:
    text: str
    score: float
    file_name: str
    page_number: int
    chunk_index: int


@dataclass(frozen=True)
class DocumentEmbedding:
    """Represents vector embedding data for a text snippet or document page."""
    text: str
    vector: List[float]
    dimensions: int
    metadata: Dict[str, Any] = field(default_factory=dict)
