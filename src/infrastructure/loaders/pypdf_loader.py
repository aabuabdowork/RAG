"""PyPDFLoader infrastructure adapter implementing IDocumentLoader."""
from pathlib import Path
from typing import Union
from langchain_community.document_loaders import PyPDFLoader

from src.domain.entities import DocumentPage, ExtractedDocument
from src.domain.interfaces.document_loader import IDocumentLoader


class PyPDFDocumentLoader(IDocumentLoader):
    """Adapter that uses LangChain's PyPDFLoader to load PDF documents."""

    def load(self, file_path: Union[str, Path]) -> ExtractedDocument:
        resolved_path = Path(file_path).resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Document file not found: {resolved_path}")

        loader = PyPDFLoader(str(resolved_path))
        raw_docs = loader.load()

        pages = [
            DocumentPage(
                page_number=idx,
                content=doc.page_content,
                metadata=doc.metadata,
            )
            for idx, doc in enumerate(raw_docs, start=1)
        ]

        return ExtractedDocument(
            source_path=str(resolved_path),
            pages=pages,
        )

