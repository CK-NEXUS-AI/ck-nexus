from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    correlation_id: str
    request_id: str
    source_sha: str | None = None
    queue_id: str | None = None


_current_trace: ContextVar[TraceContext | None] = ContextVar("ck_nexus_trace", default=None)


def set_trace_context(context: TraceContext) -> None:
    _current_trace.set(context)


def get_trace_context() -> TraceContext | None:
    return _current_trace.get()
