import argparse
from collections import Counter

from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.use_cases.ingest_folder import IngestFolderUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.core.config import settings
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader
from src.infrastructure.splitters.recursive_splitter import RecursiveTextSplitter
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore


def ingest(embedder: HuggingFaceEmbeddingService, store: QdrantVectorStore) -> None:
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


def search(
    embedder: HuggingFaceEmbeddingService,
    store: QdrantVectorStore,
    query: str,
    top_k: int,
    min_score: float,
) -> None:
    results = SearchDocumentsUseCase(embedder=embedder, store=store).execute(query, top_k, min_score)

    print(f'=== Search: "{query}" (top_k={top_k}, min_score={min_score}) ===')
    if not results:
        print("No relevant results found.")
        return
    for rank, result in enumerate(results, start=1):
        print(f"\n{rank}. score={result.score:.3f} | {result.file_name} | page {result.page_number}, chunk {result.chunk_index}")
        print(f"   {' '.join(result.text.split())[:300]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LangChain RAG system")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest", help="Index all documents in the docs folder")
    search_parser = commands.add_parser("search", help="Search indexed documents")
    search_parser.add_argument("query")
    search_parser.add_argument("--top-k", type=int, default=settings.top_k)
    search_parser.add_argument("--min-score", type=float, default=settings.min_score)
    args = parser.parse_args()

    embedder = HuggingFaceEmbeddingService()
    store = QdrantVectorStore(dimension=embedder.dimension)

    if args.command == "ingest":
        ingest(embedder, store)
    else:
        search(embedder, store, args.query, args.top_k, args.min_score)


if __name__ == "__main__":
    main()
