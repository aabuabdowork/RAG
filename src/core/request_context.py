import uuid
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    value = uuid.uuid4().hex[:8]
    request_id.set(value)
    return value
