import hashlib
import hmac
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.container import Container
from src.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return "ip:" + get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key, storage_uri=settings.rate_limit_storage)


def require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    valid = api_key and any(hmac.compare_digest(api_key.encode(), key.encode()) for key in settings.api_keys)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]
