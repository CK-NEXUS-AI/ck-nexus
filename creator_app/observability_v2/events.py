"""Privacy-safe observability contracts separated from security audit evidence."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SECRET_RE = re.compile(r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})")


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    metric: str
    value: float
    unit: str
    component: str
    correlation_id: str
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    audit_authority: bool = False

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.metric, self.unit, self.component, self.correlation_id)):
            raise ValueError("telemetry identity fields must not be empty")
        for key, value in self.labels.items():
            if _EMAIL_RE.search(value) or _SECRET_RE.search(value):
                raise ValueError(f"telemetry label {key} contains personal or secret material")


@dataclass(frozen=True, slots=True)
class RedactedDiagnostic:
    component: str
    category: str
    message_digest: str
    safe_message: str


def redact_diagnostic(component: str, category: str, message: str) -> RedactedDiagnostic:
    safe = _EMAIL_RE.sub("<redacted-email>", message)
    safe = _SECRET_RE.sub("<redacted-secret>", safe)
    return RedactedDiagnostic(
        component=component,
        category=category,
        message_digest=hashlib.sha256(message.encode()).hexdigest(),
        safe_message=safe,
    )


class MetricRegistry:
    """Small in-process reference metric store; not an audit log."""

    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def record(self, event: TelemetryEvent) -> None:
        if event.audit_authority:
            raise ValueError("telemetry cannot claim security-audit authority")
        self._events.append(event)

    def snapshot(self, *, component: str | None = None) -> tuple[TelemetryEvent, ...]:
        if component is None:
            return tuple(self._events)
        return tuple(event for event in self._events if event.component == component)
