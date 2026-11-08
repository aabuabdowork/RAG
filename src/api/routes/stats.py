from typing import Any, Dict

from fastapi import APIRouter, Query, Request

from src.api.dependencies import ContainerDep, limiter
from src.core.config import settings

router = APIRouter(tags=["monitoring"])


@router.get("/stats")
@limiter.limit(settings.rate_limit_read)
def stats(request: Request, container: ContainerDep, last: int = Query(default=10, ge=1, le=100)) -> Dict[str, Any]:
    report = container.stats()
    return {"totals": report.execute(), "requests": report.history(last)}
