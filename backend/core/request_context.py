from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return f"req_{uuid4().hex[:20]}"


def get_request_id() -> str:
    return request_id_var.get() or new_request_id()
