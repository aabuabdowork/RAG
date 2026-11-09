import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response

from src.api.dependencies import limiter, require_api_key
from src.api.routes import documents, query, stats, system
from src.container import Container
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.request_context import new_request_id, request_id
from src.domain.exceptions import BudgetExceededError, ServiceUnavailableError
from src.infrastructure.metrics.jsonl_metrics import JsonlMetrics

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    if not settings.api_keys:
        logger.warning("API_KEYS is empty: every protected endpoint will return 401.")
    container = Container(JsonlMetrics())
    container.embedder
    container.reranker
    app.state.container = container
    yield


app = FastAPI(
    title="LangChain RAG API",
    version=settings.app_version,
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.api_docs else None,
)
app.state.limiter = limiter

protected = [Depends(require_api_key)]
app.include_router(system.router)
app.include_router(query.router, dependencies=protected)
app.include_router(documents.router, dependencies=protected)
app.include_router(stats.router, dependencies=protected)


def error(status_code: int, message: str, headers: Optional[Dict[str, str]] = None) -> JSONResponse:
    return JSONResponse({"error": message, "request_id": request_id.get()}, status_code=status_code, headers=headers)


@app.middleware("http")
async def request_context(request: Request, call_next) -> Response:
    value = new_request_id()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("%s %s failed", request.method, request.url.path)
        response = error(500, "Internal server error")
    response.headers["X-Request-ID"] = value
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return error(429, f"Rate limit exceeded: {exc.detail}", {"Retry-After": str(exc.limit.limit.get_expiry())})


@app.exception_handler(BudgetExceededError)
async def budget_exceeded(request: Request, exc: BudgetExceededError) -> JSONResponse:
    return error(422, str(exc))


@app.exception_handler(ServiceUnavailableError)
async def unavailable(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    logger.error("%s %s failed: %s", request.method, request.url.path, exc, exc_info=exc)
    return error(503, f"{exc}. Please try again later.", {"Retry-After": "30"})
