from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any


class TriadRole(str, Enum):
    BUILDER = "BUILDER"
    CRITIC = "CRITIC"
    EVALUATOR = "EVALUATOR"
    GOVERNOR = "GOVERNOR"


class TriadEventType(str, Enum):
    PROPOSAL_CREATED = "proposal.created"
    OBJECTION_CREATED = "objection.created"
    PROPOSAL_REVISED = "proposal.revised"
    CANDIDATE_SUBMITTED = "candidate.submitted"
    MEASUREMENT_COMPLETED = "measurement.completed"
    CYCLE_WARNED = "cycle.warned"
    CYCLE_BRANCHED = "cycle.branched"
    CYCLE_PAUSED = "cycle.paused"
    CYCLE_CHECKPOINTED = "cycle.checkpointed"


@dataclass(frozen=True, slots=True)
class TriadEvent:
    event_id: str
    cycle_id: str
    actor: TriadRole
    event_type: TriadEventType
    payload: dict[str, Any]
    created_at: str
    causation_id: str | None = None
    correlation_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        cycle_id: str,
        actor: TriadRole,
        event_type: TriadEventType,
        payload: dict[str, Any],
        causation_id: str | None = None,
        correlation_id: str | None = None,
        created_at: str | None = None,
    ) -> "TriadEvent":
        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        body = {
            "cycle_id": cycle_id,
            "actor": actor.value,
            "event_type": event_type.value,
            "payload": payload,
            "created_at": timestamp,
            "causation_id": causation_id,
            "correlation_id": correlation_id,
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        event_id = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(
            event_id=event_id,
            cycle_id=cycle_id,
            actor=actor,
            event_type=event_type,
            payload=dict(payload),
            created_at=timestamp,
            causation_id=causation_id,
            correlation_id=correlation_id,
        )


@dataclass(slots=True)
class TriadEventBus:
    """In-memory append-only event ledger for development/runtime tests.

    This bus records events only. It grants no execution authority and performs
    no external side effects.
    """

    events: list[TriadEvent] = field(default_factory=list)

    def publish(self, event: TriadEvent) -> None:
        if any(existing.event_id == event.event_id for existing in self.events):
            return
        self.events.append(event)

    def by_cycle(self, cycle_id: str) -> tuple[TriadEvent, ...]:
        return tuple(event for event in self.events if event.cycle_id == cycle_id)

    def by_type(self, event_type: TriadEventType) -> tuple[TriadEvent, ...]:
        return tuple(event for event in self.events if event.event_type is event_type)
