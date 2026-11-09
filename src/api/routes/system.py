from typing import Callable

from fastapi import APIRouter, Response

from src.api.dependencies import ContainerDep
from src.api.schemas import HealthResponse
from src.container import Container
from src.core.config import settings
from src.domain.entities import DocumentStatus

router = APIRouter(tags=["system"])


def check(probe: Callable[[], object]) -> str:
    try:
        probe()
        return "ok"
    except Exception as error:
        return f"down ({type(error).__name__})"


def report(container: Container) -> HealthResponse:
    checks = {
        "qdrant": check(container.store.count),
        "supabase": check(lambda: container.repository.list(DocumentStatus.FAILED)),
        "llm": "ok" if settings.openai_api_key else "missing (OPENROUTER_API_KEY)",
        "api_keys": "ok" if settings.api_keys else "missing (API_KEYS)",
    }
    return HealthResponse(
        status="ok" if all(value == "ok" for value in checks.values()) else "degraded",
        environment=settings.app_env,
        version=settings.app_version,
        commit=settings.git_commit,
        checks=checks,
    )


@router.get("/health", response_model=HealthResponse)
def health(container: ContainerDep) -> HealthResponse:
    return report(container)


@router.get("/ready", response_model=HealthResponse)
def ready(container: ContainerDep, response: Response) -> HealthResponse:
    result = report(container)
    if result.status != "ok":
        response.status_code = 503
    return result
