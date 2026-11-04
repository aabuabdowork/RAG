import argparse
from collections import Counter

from src.application.use_cases.ask_question import AskQuestionUseCase
from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.use_cases.ingest_folder import IngestFolderUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.core.config import settings
from src.domain.entities import SearchResult
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.llm.openrouter_service import OpenRouterLLMService
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


def search(search_documents: SearchDocumentsUseCase, args: argparse.Namespace) -> None:
    results = search_documents.execute(args.query, args.top_k, args.min_score, args.department)

    print_header("Search", args)
    if not results:
        print("No relevant results found.")
        return
    for rank, result in enumerate(results, start=1):
        print(f"\n{describe(rank, result)}")
        print(f"   {' '.join(result.text.split())[:300]}")


def ask(search_documents: SearchDocumentsUseCase, args: argparse.Namespace) -> None:
    ask_question = AskQuestionUseCase(search=search_documents, llm=OpenRouterLLMService())
    answer = ask_question.execute(args.query, args.top_k, args.min_score, args.department)

    print_header("Ask", args)
    print(f"\n{answer.text}")
    if answer.sources:
        print("\nSources:")
        for rank, source in enumerate(answer.sources, start=1):
            print(describe(rank, source))


def print_header(command: str, args: argparse.Namespace) -> None:
    scope = args.department.upper() if args.department else "ALL"
    print(f'=== {command}: "{args.query}" (department={scope}, top_k={args.top_k}, min_score={args.min_score}) ===')


def describe(rank: int, result: SearchResult) -> str:
    return (
        f"{rank}. score={result.score:.3f} | {result.department}/{result.file_name} "
        f"| page {result.page_number}, chunk {result.chunk_index}"
    )


def main() -> None:
    query_options = argparse.ArgumentParser(add_help=False)
    query_options.add_argument("query")
    query_options.add_argument("--top-k", type=int, default=settings.top_k)
    query_options.add_argument("--min-score", type=float, default=settings.min_score)
    query_options.add_argument("--department", default=None)

    parser = argparse.ArgumentParser(description="LangChain RAG system")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest", help="Index all documents in the departments folder")
    commands.add_parser("search", parents=[query_options], help="Search indexed documents")
    commands.add_parser("ask", parents=[query_options], help="Answer a question from the documents")
    args = parser.parse_args()

    embedder = HuggingFaceEmbeddingService()
    store = QdrantVectorStore(dimension=embedder.dimension)

    if args.command == "ingest":
        ingest(embedder, store)
        return

    search_documents = SearchDocumentsUseCase(embedder=embedder, store=store)
    if args.command == "search":
        search(search_documents, args)
    else:
        ask(search_documents, args)


if __name__ == "__main__":
    main()
