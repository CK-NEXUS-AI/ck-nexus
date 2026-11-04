"""Content-addressed evidence contracts for CK-NEXUS runtime events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceEvent:
    event_id: str
    event_type: str
    task_id: str
    run_id: str
    correlation_id: str
    causation_id: str | None
    actor: str
    policy_decision: str
    input_digest: str
    output_digest: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_digest: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.event_id,
            self.event_type,
            self.task_id,
            self.run_id,
            self.correlation_id,
            self.actor,
            self.policy_decision,
            self.input_digest,
            self.output_digest,
            self.timestamp,
        )
        if any(not item.strip() for item in required):
            raise ValueError("evidence event required fields must not be empty")
        for digest in (self.input_digest, self.output_digest):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("input/output digests must be lowercase SHA-256")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "actor": self.actor,
            "policy_decision": self.policy_decision,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "previous_digest": self.previous_digest,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(encoded).hexdigest()


class EvidenceChain:
    """Append-only reference chain. Durable persistence belongs to CK-NEXUS storage."""

    def __init__(self) -> None:
        self._events: list[EvidenceEvent] = []

    def append(self, event: EvidenceEvent) -> str:
        expected_previous = self._events[-1].digest if self._events else None
        if event.previous_digest != expected_previous:
            raise ValueError("evidence previous_digest does not match current chain head")
        if any(existing.event_id == event.event_id for existing in self._events):
            raise ValueError("event_id already exists")
        self._events.append(event)
        return event.digest

    def verify(self) -> bool:
        previous: str | None = None
        for event in self._events:
            if event.previous_digest != previous:
                return False
            previous = event.digest
        return True

    def events(self) -> tuple[EvidenceEvent, ...]:
        return tuple(self._events)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()
