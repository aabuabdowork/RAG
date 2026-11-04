"""Domain entities representing core business models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    DENSE = "dense"
    SPARSE = "sparse"


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
    department: str
    file_name: str
    page_number: int
    chunk_index: int


@dataclass(frozen=True)
class Answer:
    text: str
    sources: List[SearchResult]
    tokens: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentEmbedding:
    """Represents vector embedding data for a text snippet or document page."""
    text: str
    vector: List[float]
    dimensions: int
    metadata: Dict[str, Any] = field(default_factory=dict)
