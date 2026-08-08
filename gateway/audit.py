from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GatewayAuditEvent:
    correlation_id: str
    route_id: str
    tenant_id: str
    actor_id: str
    method: str
    status_code: int
    decision: str
    policy_version: str
    occurred_at: str

    @classmethod
    def create(cls, **kwargs: object) -> "GatewayAuditEvent":
        return cls(occurred_at=datetime.now(UTC).isoformat(), **kwargs)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class AuditSink(Protocol):
    async def emit(self, event: GatewayAuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[GatewayAuditEvent] = []

    async def emit(self, event: GatewayAuditEvent) -> None:
        self.events.append(event)
