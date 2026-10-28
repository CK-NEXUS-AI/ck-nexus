"""Deterministic n8n signal analysis with bounded, secret-safe output."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from .models import DevelopmentSignal

_MAX_MESSAGE = 1000
_SECRET_PATTERNS = (
    re.compile(
        r"(?i)((?:api[_-]?key|token|password|secret|authorization)\s*[:=])\s*(?:bearer\s+)?[^\s,;]+"
    ),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
)


def sanitize_message(text: str) -> str:
    value = str(text or "")
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(lambda match: match.group(1) + "[REDACTED]", value)
    return value[:_MAX_MESSAGE]


def fingerprint_execution(execution: dict[str, object]) -> str:
    payload = {
        "id": execution.get("id"),
        "workflowId": execution.get("workflowId"),
        "status": execution.get("status"),
        "stoppedAt": execution.get("stoppedAt"),
        "error": _error_message(execution),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def classify_execution(
    execution: dict[str, object], slow_seconds: float
) -> DevelopmentSignal | None:
    execution_id = str(execution.get("id") or "")
    if not execution_id:
        return None
    status = str(execution.get("status") or "").lower()
    workflow_id = str(execution.get("workflowId") or "unknown")
    workflow_name = str(execution.get("workflowName") or workflow_id)
    duration = _duration_seconds(execution)
    if status in {"error", "failed", "crashed", "canceled", "cancelled"}:
        message = sanitize_message(_error_message(execution) or f"n8n execution status: {status}")
        return DevelopmentSignal(
            fingerprint_execution(execution),
            execution_id,
            "bug",
            "high",
            f"Fix n8n workflow failure: {workflow_name}",
            f"Workflow {workflow_id} execution {execution_id} failed: {message}",
            2,
        )
    if duration is not None and duration > slow_seconds:
        return DevelopmentSignal(
            fingerprint_execution(execution),
            execution_id,
            "performance",
            "warning",
            f"Investigate slow n8n workflow: {workflow_name}",
            f"Workflow {workflow_id} execution {execution_id} took {duration:.1f}s.",
            2,
        )
    return None


def priority_for(category: str, repeat_count: int) -> int:
    base = {"bug": 2, "reliability": 2, "performance": 2, "workflow": 1}.get(category, 1)
    return min(3, base + (1 if repeat_count >= 3 else 0))


def _error_message(execution: dict[str, object]) -> str:
    error = execution.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("description") or "")
    return str(error or execution.get("errorMessage") or "")


def _duration_seconds(execution: dict[str, object]) -> float | None:
    value = execution.get("duration")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    started = _parse_time(execution.get("startedAt"))
    stopped = _parse_time(execution.get("stoppedAt"))
    if started is not None and stopped is not None:
        return max(0.0, (stopped - started).total_seconds())
    return None


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
