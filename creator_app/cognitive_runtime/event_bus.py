from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

ALLOWED_FAMILIES = {
    "task", "agent", "tool", "policy", "approval", "verification", "evidence"
}
TRUTH_CLASSES = {
    "DISCOVERED", "OBSERVED", "INFERRED", "VERIFIED", "NOT_VERIFIED", "STALE"
}


class EventContractError(ValueError):
    """Raised when a runtime event violates the public event contract."""


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    event_id: str
    event_type: str
    subject_sha: str
    timestamp: str
    truth_class: str
    payload: dict[str, Any]
    task_id: str = ""
    run_id: str = ""
    node_id: str = ""
    agent_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    input_digest: str = ""
    output_digest: str = ""
    evidence_id: str = ""

    @property
    def family(self) -> str:
        return self.event_type.split(".", 1)[0]

    def canonical_digest(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    def validate(self, expected_subject_sha: str) -> None:
        if not self.event_id or not self.event_type or "." not in self.event_type:
            raise EventContractError("event identity/type missing")
        if self.family not in ALLOWED_FAMILIES:
            raise EventContractError(f"unsupported event family: {self.family}")
        if self.subject_sha != expected_subject_sha:
            raise EventContractError("subject mismatch")
        if self.truth_class not in TRUTH_CLASSES:
            raise EventContractError("invalid truth class")
        if self.truth_class == "VERIFIED" and (not self.evidence_id or not self.output_digest):
            raise EventContractError("verified event missing evidence binding")


class RuntimeEventBus:
    """Append-only, exact-subject runtime event store with duplicate protection."""

    def __init__(self, subject_sha: str) -> None:
        self.subject_sha = subject_sha
        self._events: list[RuntimeEvent] = []
        self._digests: dict[str, str] = {}

    def append(self, event: RuntimeEvent) -> bool:
        event.validate(self.subject_sha)
        digest = event.canonical_digest()
        previous = self._digests.get(event.event_id)
        if previous is not None:
            if previous != digest:
                raise EventContractError("conflicting duplicate event_id")
            return False
        self._events.append(event)
        self._digests[event.event_id] = digest
        return True

    def events(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)

    def replay_order(self) -> tuple[RuntimeEvent, ...]:
        return tuple(sorted(self._events, key=lambda e: (e.timestamp, e.event_id)))

