import argparse
from collections import Counter
from typing import Any, Dict, List, Tuple

from langsmith import traceable

from src.application.use_cases.ask_question import AskQuestionUseCase
from src.application.use_cases.delete_document import DeleteDocumentUseCase
from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.expand_query import ExpandQueryUseCase
from src.application.use_cases.index_documents import IndexDocumentsUseCase
from src.application.use_cases.reconcile import ReconcileUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.application.use_cases.upload_document import UploadDocumentUseCase
from src.application.use_cases.upload_folder import UploadFolderUseCase
from src.core.config import settings
from src.domain.entities import Answer, Retrieval, SearchMode, SearchResult
from src.domain.exceptions import BudgetExceededError
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.llm.openrouter_service import OpenRouterLLMService
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader
from src.infrastructure.rerankers.cross_encoder_reranker import CrossEncoderReranker
from src.infrastructure.splitters.recursive_splitter import RecursiveTextSplitter
from src.infrastructure.supabase.client import create_supabase_client
from src.infrastructure.supabase.document_repository import SupabaseDocumentRepository
from src.infrastructure.supabase.object_storage import SupabaseObjectStorage
from src.infrastructure.tokenizers.tiktoken_counter import TiktokenCounter
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore

DOCUMENT_COMMANDS = {"upload", "index", "ingest", "delete", "reconcile"}


def command_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return vars(inputs["args"])


@traceable(name="documents", run_type="chain", process_inputs=command_inputs)
def manage_documents(args: argparse.Namespace) -> None:
    client = create_supabase_client()
    repository = SupabaseDocumentRepository(client)
    storage = SupabaseObjectStorage(client)

    if args.command in ("upload", "ingest"):
        upload = UploadFolderUseCase(UploadDocumentUseCase(repository, storage))
        report(f"Upload {settings.docs_dir}", upload.execute(settings.docs_dir))
    if args.command == "upload":
        return

    embedder = HuggingFaceEmbeddingService()
    store = QdrantVectorStore(dimension=embedder.dimension)

    if args.command == "delete":
        print(DeleteDocumentUseCase(repository, storage, store).execute(*args.document))
        return
    if args.command == "reconcile":
        report("Reconcile", ReconcileUseCase(repository, store).execute())

    embed = EmbedDocumentUseCase(
        loader=PyPDFDocumentLoader(),
        splitter=RecursiveTextSplitter(),
        embedder=embedder,
    )
    report("Index", IndexDocumentsUseCase(repository, storage, embed, store).execute())
    print(f"\nPoints in '{settings.qdrant_collection}': {store.count()}")


def report(title: str, results: Dict[str, str]) -> None:
    print(f"\n=== {title} ===")
    if not results:
        print("Nothing to do.")
    for key, status in results.items():
        print(f"{status:<15} {key}")
    if results:
        print(f"Summary: {dict(Counter(status.split(' ')[0] for status in results.values()))}")


def document_key(value: str) -> Tuple[str, str]:
    department, _, file_name = value.partition("/")
    if not department or not file_name:
        raise argparse.ArgumentTypeError("use DEPARTMENT/file_name, e.g. HR/remote_work_policy.pdf")
    return department, file_name


@traceable(name="search", run_type="chain", process_inputs=command_inputs)
def search(search_documents: SearchDocumentsUseCase, args: argparse.Namespace) -> Retrieval:
    retrieval = search_documents.execute(
        args.query, args.top_k, args.min_score, args.department, SearchMode(args.mode)
    )

    print_header("Search", args)
    print_queries(retrieval.queries)
    if not retrieval.results:
        print("\nNo relevant results found.")
    for rank, result in enumerate(retrieval.results, start=1):
        print(f"\n{describe(rank, result)}")
        print(f"   {' '.join(result.text.split())[:300]}")
    return retrieval


@traceable(name="ask", run_type="chain", process_inputs=command_inputs)
def ask(ask_question: AskQuestionUseCase, args: argparse.Namespace) -> Answer:
    answer = ask_question.execute(
        args.query, args.top_k, args.min_score, args.department, SearchMode(args.mode)
    )

    print_header("Ask", args)
    print_queries(answer.queries)
    print(f"\n{answer.text}")
    if answer.sources:
        print("\nSources:")
        for rank, source in enumerate(answer.sources, start=1):
            print(describe(rank, source))
    print("\nTokens: " + " | ".join(f"{part} {count}" for part, count in answer.tokens.items()))
    return answer


def print_header(command: str, args: argparse.Namespace) -> None:
    scope = args.department.upper() if args.department else "ALL"
    print(
        f'=== {command}: "{args.query}" (mode={args.mode}, rerank={args.rerank}, '
        f"multi_query={args.multi_query}, department={scope}, top_k={args.top_k}) ==="
    )


def print_queries(queries: List[str]) -> None:
    if len(queries) < 2:
        return
    print("\nQueries:")
    print(f"  original : {queries[0]}")
    for number, variant in enumerate(queries[1:], start=1):
        print(f"  variant {number}: {variant}")


def describe(rank: int, result: SearchResult) -> str:
    rerank = f" rerank={result.rerank_score:.3f}" if result.rerank_score is not None else ""
    return (
        f"{rank}. score={result.score:.3f}{rerank} | {result.department}/{result.file_name} "
        f"| page {result.page_number}, chunk {result.chunk_index}"
    )


def parse_args() -> argparse.Namespace:
    query_options = argparse.ArgumentParser(add_help=False)
    query_options.add_argument("query")
    query_options.add_argument("--top-k", type=int, default=settings.top_k)
    query_options.add_argument("--min-score", type=float, default=settings.min_score)
    query_options.add_argument("--department", default=None)
    query_options.add_argument("--mode", choices=[mode.value for mode in SearchMode], default=settings.search_mode)
    query_options.add_argument("--rerank", action=argparse.BooleanOptionalAction, default=settings.rerank_enabled)
    query_options.add_argument(
        "--multi-query", action=argparse.BooleanOptionalAction, default=settings.multi_query_enabled
    )

    parser = argparse.ArgumentParser(description="LangChain RAG system")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("upload", help="Upload the departments folder to Supabase")
    commands.add_parser("index", help="Index pending Supabase documents into Qdrant")
    commands.add_parser("ingest", help="Upload, then index")
    commands.add_parser("reconcile", help="Repair Supabase and Qdrant drift, then index")
    commands.add_parser("delete", help="Delete a document everywhere").add_argument("document", type=document_key)
    commands.add_parser("search", parents=[query_options], help="Search indexed documents")
    commands.add_parser("ask", parents=[query_options], help="Answer a question from the documents")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command in DOCUMENT_COMMANDS:
        manage_documents(args)
        return

    embedder = HuggingFaceEmbeddingService()
    store = QdrantVectorStore(dimension=embedder.dimension)

    counter = TiktokenCounter()
    llm = OpenRouterLLMService() if args.command == "ask" or args.multi_query else None
    expander = (
        ExpandQueryUseCase(llm, counter, settings.max_query_variants, settings.max_question_tokens)
        if args.multi_query
        else None
    )
    search_documents = SearchDocumentsUseCase(
        embedder=embedder,
        store=store,
        max_top_k=settings.max_top_k,
        reranker=CrossEncoderReranker() if args.rerank else None,
        expander=expander,
        rerank_candidates=settings.rerank_candidates,
        multi_query_candidates=settings.multi_query_candidates,
    )

    try:
        if args.command == "search":
            search(search_documents, args)
        else:
            ask_question = AskQuestionUseCase(
                search=search_documents,
                llm=llm,
                counter=counter,
                max_question_tokens=settings.max_question_tokens,
                max_context_tokens=settings.max_context_tokens,
            )
            ask(ask_question, args)
    except BudgetExceededError as error:
        print(f"Rejected: {error}")


if __name__ == "__main__":
    main()
