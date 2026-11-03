from collections import Counter

from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.use_cases.ingest_folder import IngestFolderUseCase
from src.core.config import settings
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader
from src.infrastructure.splitters.recursive_splitter import RecursiveTextSplitter
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore


def main() -> None:
    embedder = HuggingFaceEmbeddingService()
    store = QdrantVectorStore(dimension=embedder.dimension)

    embed = EmbedDocumentUseCase(
        loader=PyPDFDocumentLoader(),
        splitter=RecursiveTextSplitter(),
        embedder=embedder,
    )
    ingest_folder = IngestFolderUseCase(IngestDocumentUseCase(embed=embed, store=store))

    print(f"=== Ingesting {settings.docs_dir} ===")
    results = ingest_folder.execute(settings.docs_dir)
    for file_name, status in results.items():
        print(f"{status:<10} {file_name}")

    summary = Counter(status.split(" ")[0] for status in results.values())
    print(f"\nSummary: {dict(summary)}")
    print(f"Points in '{settings.qdrant_collection}': {store.count()}")


if __name__ == "__main__":
    main()
