from typing import Any, Dict

from fastapi import APIRouter, Request
from langsmith import traceable

from src.api.dependencies import ContainerDep, limiter
from src.api.schemas import AskResponse, QueryRequest, SearchResponse, Source
from src.application.observe import observe
from src.application.use_cases.ask_question import AskQuestionUseCase
from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.core.config import settings
from src.core.request_context import request_id
from src.domain.entities import Answer, Retrieval

router = APIRouter(tags=["query"])


def body_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return inputs["body"].model_dump(mode="json")


def fields(body: QueryRequest) -> Dict[str, Any]:
    return {"channel": "api", **body.model_dump(mode="json", exclude={"top_k", "min_score"})}


@traceable(name="ask", run_type="chain", process_inputs=body_inputs)
def run_ask(use_case: AskQuestionUseCase, body: QueryRequest) -> Answer:
    return use_case.execute(body.query, body.top_k, body.min_score, body.department, body.mode)


@traceable(name="search", run_type="chain", process_inputs=body_inputs)
def run_search(use_case: SearchDocumentsUseCase, body: QueryRequest) -> Retrieval:
    return use_case.execute(body.query, body.top_k, body.min_score, body.department, body.mode)


@router.post("/ask", response_model=AskResponse)
@limiter.limit(settings.rate_limit_ask)
def ask(request: Request, body: QueryRequest, container: ContainerDep) -> AskResponse:
    use_case = container.ask(body.rerank, body.multi_query)
    answer = observe(
        container.metrics, "ask", lambda: run_ask(use_case, body), lambda a: {"found": a.found}, **fields(body)
    )
    return AskResponse(
        request_id=request_id.get(),
        answer=answer.text,
        found=answer.found,
        sources=[Source.of(source) for source in answer.sources] if answer.found else [],
        queries=answer.queries,
        tokens=answer.tokens,
    )


@router.post("/search", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_search)
def search(request: Request, body: QueryRequest, container: ContainerDep) -> SearchResponse:
    use_case = container.search(body.rerank, body.multi_query)
    retrieval = observe(
        container.metrics,
        "search",
        lambda: run_search(use_case, body),
        lambda r: {"found": bool(r.results)},
        **fields(body),
    )
    return SearchResponse(
        request_id=request_id.get(),
        queries=retrieval.queries,
        results=[Source.of(result, with_text=True) for result in retrieval.results],
    )
