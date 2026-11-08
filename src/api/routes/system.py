from typing import Callable, Dict

from fastapi import APIRouter, Response

from src.api.dependencies import ContainerDep
from src.core.config import settings
from src.domain.entities import DocumentStatus

router = APIRouter(tags=["system"])


def check(probe: Callable[[], object]) -> str:
    try:
        probe()
        return "ok"
    except Exception as error:
        return f"down ({type(error).__name__})"


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(container: ContainerDep, response: Response) -> Dict[str, str]:
    checks = {
        "qdrant": check(lambda: container.store.count()),
        "supabase": check(lambda: container.repository.list(DocumentStatus.FAILED)),
        "llm": "ok" if settings.openai_api_key else "down (no API key)",
    }
    if any(value != "ok" for value in checks.values()):
        response.status_code = 503
    return checks
