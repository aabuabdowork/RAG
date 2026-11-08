from functools import wraps
from typing import Any, Callable, TypeVar

import httpx

from src.domain.exceptions import ServiceUnavailableError

F = TypeVar("F", bound=Callable[..., Any])


def supabase_call(function: F) -> F:
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except httpx.TransportError as error:
            raise ServiceUnavailableError("Supabase", error) from error

    return wrapper
