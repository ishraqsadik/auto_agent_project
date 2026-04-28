"""Request-scoped IDs for tools (set by webhook / crew runner)."""

from contextvars import ContextVar

current_call_db_id: ContextVar[int | None] = ContextVar("current_call_db_id", default=None)
current_customer_db_id: ContextVar[int | None] = ContextVar("current_customer_db_id", default=None)
