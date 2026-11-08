import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langsmith import get_current_run_tree, traceable

from src.application.observe import observe, status_of
from src.application.use_cases.ask_question import AskQuestionUseCase
from src.application.use_cases.evaluate import EvalCase, EvalResult, EvaluateUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.application.use_cases.upload_folder import UploadFolderUseCase
from src.container import Container
from src.core.config import settings
from src.core.logging import LOG_FILE, setup_logging
from src.core.request_context import new_request_id
from src.domain.entities import Answer, Retrieval, SearchMode, SearchResult
from src.infrastructure.metrics.jsonl_metrics import JsonlMetrics

DOCUMENT_COMMANDS = {"upload", "index", "ingest", "delete", "reconcile"}
EXIT_CODES = {"error": 1, "rejected": 2, "unavailable": 3}
MESSAGES = {
    "rejected": "Rejected: {error}",
    "unavailable": "Unavailable: {error}. Please try again later.",
    "error": "Unexpected error ({name}). Details: " + str(LOG_FILE),
}

logger = logging.getLogger("main")


def command_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return vars(inputs["args"])


def tag_run(**metadata: Any) -> None:
    run = get_current_run_tree()
    if run:
        run.add_metadata(metadata)


@traceable(name="documents", run_type="chain", process_inputs=command_inputs)
def manage_documents(container: Container, args: argparse.Namespace) -> None:
    if args.command in ("upload", "ingest"):
        report(f"Upload {settings.docs_dir}", UploadFolderUseCase(container.upload()).execute(settings.docs_dir))
    if args.command == "upload":
        return
    if args.command == "delete":
        print(container.delete().execute(*args.document))
        return
    if args.command == "reconcile":
        report("Reconcile", container.reconcile().execute())

    report("Index", container.index_pending())
    print(f"\nPoints in '{settings.qdrant_collection}': {container.store.count()}")


@traceable(name="search", run_type="chain", process_inputs=command_inputs)
def search(search_documents: SearchDocumentsUseCase, args: argparse.Namespace) -> Retrieval:
    retrieval = search_documents.execute(
        args.query, args.top_k, args.min_score, args.department, SearchMode(args.mode)
    )
    tag_run(found=bool(retrieval.results))

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
    tag_run(found=answer.found)

    print_header("Ask", args)
    print_queries(answer.queries)
    print(f"\n{answer.text}")
    if answer.sources:
        print("\nSources:")
        for rank, source in enumerate(answer.sources, start=1):
            print(describe(rank, source))
    print("\nTokens: " + " | ".join(f"{part} {count}" for part, count in answer.tokens.items()))
    return answer


@traceable(name="evaluate", run_type="chain", process_inputs=command_inputs)
def evaluate(evaluator: EvaluateUseCase, args: argparse.Namespace) -> List[EvalResult]:
    cases = [EvalCase(**item) for item in json.loads(args.dataset.read_text(encoding="utf-8"))]
    print(
        f"=== Evaluate: {len(cases)} cases (mode={args.mode}, rerank={args.rerank}, "
        f"multi_query={args.multi_query}, top_k={args.top_k}) ===\n"
    )
    results = evaluator.execute(cases, args.top_k, args.min_score, SearchMode(args.mode))
    for number, result in enumerate(results, start=1):
        scope = f" [{result.case.department}]" if result.case.department else ""
        print(
            f"{number:>2}. retrieved {mark(result.retrieved)}  correct {mark(result.correct)}  "
            f"cited {mark(result.cited)}  | {result.case.question}{scope}"
        )
    print(
        f"\nRetrieval: {rate([r.retrieved for r in results])} | "
        f"Correct: {rate([r.correct for r in results])} | "
        f"Cited: {rate([r.cited for r in results])}"
    )
    return results


def report(title: str, results: Dict[str, str]) -> None:
    print(f"\n=== {title} ===")
    if not results:
        print("Nothing to do.")
    for key, status in results.items():
        print(f"{status:<15} {key}")
    if results:
        print(f"Summary: {dict(Counter(status.split(' ')[0] for status in results.values()))}")


def print_stats(title: str, stats: Dict[str, Dict[str, Any]]) -> None:
    print(f"\n=== {title} ===")
    for name, values in stats.items():
        print(f"{name:<7}" + " | ".join(f"{key} {value}" for key, value in values.items()))


def print_history(rows: List[Dict[str, Any]]) -> None:
    print(f"\n=== Last {len(rows)} requests ===")
    for row in rows:
        print(" | ".join(f"{key} {value}" for key, value in row.items()))


def print_header(command: str, args: argparse.Namespace) -> None:
    scope = args.department.upper() if args.department else "ALL"
    print(
        f'=== {command}: "{args.query}" (mode={args.mode}, rerank={args.rerank}, '
        f"multi_query={args.multi_query}, cache={args.cache}, department={scope}, top_k={args.top_k}) ==="
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


def mark(value: Optional[bool]) -> str:
    return "–" if value is None else "✅" if value else "❌"


def rate(values: List[Optional[bool]]) -> str:
    scored = [value for value in values if value is not None]
    return f"{sum(scored)}/{len(scored)} ({sum(scored) / len(scored):.0%})" if scored else "n/a"


def document_key(value: str) -> Tuple[str, str]:
    department, _, file_name = value.partition("/")
    if not department or not file_name:
        raise argparse.ArgumentTypeError("use DEPARTMENT/file_name, e.g. HR/remote_work_policy.pdf")
    return department, file_name


def parse_args() -> argparse.Namespace:
    retrieval_options = argparse.ArgumentParser(add_help=False)
    retrieval_options.add_argument("--top-k", type=int, default=settings.top_k)
    retrieval_options.add_argument("--min-score", type=float, default=settings.min_score)
    retrieval_options.add_argument("--mode", choices=[mode.value for mode in SearchMode], default=settings.search_mode)
    retrieval_options.add_argument("--rerank", action=argparse.BooleanOptionalAction, default=settings.rerank_enabled)
    retrieval_options.add_argument(
        "--multi-query", action=argparse.BooleanOptionalAction, default=settings.multi_query_enabled
    )
    retrieval_options.add_argument("--cache", action=argparse.BooleanOptionalAction, default=settings.cache_enabled)

    query_options = argparse.ArgumentParser(add_help=False, parents=[retrieval_options])
    query_options.add_argument("query")
    query_options.add_argument("--department", default=None)

    parser = argparse.ArgumentParser(description="LangChain RAG system")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("upload", help="Upload the departments folder to Supabase")
    commands.add_parser("index", help="Index pending Supabase documents into Qdrant")
    commands.add_parser("ingest", help="Upload, then index")
    commands.add_parser("reconcile", help="Repair Supabase and Qdrant drift, then index")
    commands.add_parser("delete", help="Delete a document everywhere").add_argument("document", type=document_key)
    commands.add_parser("search", parents=[query_options], help="Search indexed documents")
    commands.add_parser("ask", parents=[query_options], help="Answer a question from the documents")
    commands.add_parser(
        "evaluate", parents=[retrieval_options], help="Score answers against the evaluation dataset"
    ).add_argument("--dataset", type=Path, default=settings.eval_dataset)
    commands.add_parser(
        "stats", help="Show totals and per-request details from logs/metrics.jsonl"
    ).add_argument("--last", type=int, default=10)
    return parser.parse_args()


def run(container: Container, args: argparse.Namespace, request_id: str) -> None:
    if args.command in DOCUMENT_COMMANDS:
        manage_documents(container, args)
        return
    if args.command == "stats":
        stats = container.stats()
        print_stats("Totals", stats.execute())
        print_history(stats.history(args.last))
        return

    fields = {
        "channel": "cli",
        "query": getattr(args, "query", None),
        "department": getattr(args, "department", None),
        "mode": args.mode,
        "rerank": args.rerank,
        "multi_query": args.multi_query,
        "cache": args.cache,
    }
    if args.command == "search":
        use_case = container.search(args.rerank, args.multi_query)
        observe(container.metrics, "search", lambda: search(use_case, args), lambda r: {"found": bool(r.results)}, **fields)
    elif args.command == "ask":
        use_case = container.ask(args.rerank, args.multi_query)
        observe(container.metrics, "ask", lambda: ask(use_case, args), lambda a: {"found": a.found}, **fields)
    else:
        evaluator = EvaluateUseCase(container.ask(args.rerank, args.multi_query))
        observe(
            container.metrics,
            "evaluate",
            lambda: evaluate(evaluator, args),
            lambda results: {"cases": len(results), "correct": sum(r.correct for r in results)},
            **fields,
        )
        stats = container.stats().execute(request_id)
        print_stats("This run", {"llm": stats["llm"], "cache": stats["cache"]})


def main() -> int:
    setup_logging()
    args = parse_args()
    request_id = new_request_id()
    container = Container(JsonlMetrics(), cache_enabled=getattr(args, "cache", settings.cache_enabled))
    try:
        run(container, args, request_id)
    except Exception as error:
        status = status_of(error)
        if status != "rejected":
            logger.exception("%s failed", args.command)
        print(MESSAGES[status].format(error=error, name=type(error).__name__))
        return EXIT_CODES[status]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
