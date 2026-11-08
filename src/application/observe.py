import time
from typing import Any, Callable, Dict, TypeVar

from src.domain.exceptions import BudgetExceededError, ServiceUnavailableError
from src.domain.interfaces.metrics import IMetrics

T = TypeVar("T")


def status_of(error: Exception) -> str:
    if isinstance(error, BudgetExceededError):
        return "rejected"
    if isinstance(error, ServiceUnavailableError):
        return "unavailable"
    return "error"


def observe(
    metrics: IMetrics,
    event: str,
    action: Callable[[], T],
    summary: Callable[[T], Dict[str, Any]],
    **fields: Any,
) -> T:
    started = time.perf_counter()
    try:
        result = action()
    except Exception as error:
        metrics.record(event, status=status_of(error), **fields)
        raise
    latency_ms = round((time.perf_counter() - started) * 1000)
    metrics.record(event, status="ok", latency_ms=latency_ms, **summary(result), **fields)
    return result
