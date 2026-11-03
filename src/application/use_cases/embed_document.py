"""Use case for generating vector embeddings from documents."""
from pathlib import Path
from typing import List, Union

from src.domain.entities import DocumentEmbedding
from src.domain.interfaces.document_loader import IDocumentLoader
from src.domain.interfaces.embedding_service import IEmbeddingService


class EmbedDocumentUseCase:
    """Use case to load documents and generate vector embeddings."""

    def __init__(self, loader: IDocumentLoader, embedder: IEmbeddingService) -> None:
        self._loader = loader
        self._embedder = embedder

    def execute(self, file_path: Union[str, Path]) -> List[DocumentEmbedding]:
        document = self._loader.load(file_path)
        texts = [page.content for page in document.pages]
        vectors = self._embedder.embed_documents(texts)

        results: List[DocumentEmbedding] = []
        for page, vector in zip(document.pages, vectors):
            results.append(
                DocumentEmbedding(
                    text=page.content.strip(),
                    vector=vector,
                    dimensions=len(vector),
                    metadata={
                        **page.metadata,
                        "page_number": page.page_number,
                        "source": document.source_path,
                    },
                )
            )
        return results

