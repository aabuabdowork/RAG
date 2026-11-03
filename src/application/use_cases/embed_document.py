from pathlib import Path
from typing import List, Union

from src.domain.entities import DocumentEmbedding
from src.domain.interfaces.document_loader import IDocumentLoader
from src.domain.interfaces.embedding_service import IEmbeddingService
from src.domain.interfaces.text_splitter import ITextSplitter


class EmbedDocumentUseCase:
    def __init__(
        self,
        loader: IDocumentLoader,
        splitter: ITextSplitter,
        embedder: IEmbeddingService,
    ) -> None:
        self._loader = loader
        self._splitter = splitter
        self._embedder = embedder

    def execute(self, file_path: Union[str, Path]) -> List[DocumentEmbedding]:
        document = self._loader.load(file_path)

        chunks = [
            (page, index, text)
            for page in document.pages
            for index, text in enumerate(self._splitter.split(page.content), start=1)
        ]
        vectors = self._embedder.embed_documents([text for _, _, text in chunks])

        return [
            DocumentEmbedding(
                text=text,
                vector=vector,
                dimensions=len(vector),
                metadata={
                    **page.metadata,
                    "source": document.source_path,
                    "page_number": page.page_number,
                    "chunk_index": index,
                },
            )
            for (page, index, text), vector in zip(chunks, vectors)
        ]
