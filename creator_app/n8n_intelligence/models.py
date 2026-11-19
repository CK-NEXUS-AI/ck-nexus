"""Contracts for normalized n8n telemetry and development signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_SEVERITIES = {"info", "warning", "high", "critical"}
_EVENT_CATEGORIES = {"success", "failure", "performance", "reliability", "workflow"}
_SIGNAL_CATEGORIES = {"bug", "performance", "reliability", "workflow"}


@dataclass(frozen=True, slots=True)
class N8NExecutionEvent:
    event_id: str
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: str
    severity: str
    category: str
    message: str
    observed_at: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.execution_id.strip():
            raise ValueError("event and execution ids must not be empty")
        if self.severity not in _SEVERITIES:
            raise ValueError("invalid severity")
        if self.category not in _EVENT_CATEGORIES:
            raise ValueError("invalid event category")
        if len(self.message) > 1000:
            raise ValueError("message exceeds 1000 characters")

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "observed_at": self.observed_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class DevelopmentSignal:
    event_id: str
    execution_id: str
    category: str
    severity: str
    title: str
    description: str
    priority: int

    def __post_init__(self) -> None:
        if self.category not in _SIGNAL_CATEGORIES:
            raise ValueError("invalid signal category")
        if self.severity not in _SEVERITIES:
            raise ValueError("invalid severity")
        if not 0 <= self.priority <= 3:
            raise ValueError("priority must be between 0 and 3")
        if not self.title.strip() or not self.description.strip():
            raise ValueError("signal text must not be empty")
