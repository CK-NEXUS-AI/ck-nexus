from __future__ import annotations

import json
from collections.abc import Iterable
from copy import deepcopy
from hashlib import sha256
from typing import Any

from .event_bus import RuntimeEvent


class ProjectionError(ValueError):
    """Raised when public state cannot be projected safely."""


class StateProjector:
    """Deterministic public state derived only from validated runtime events."""

    def __init__(self, subject_sha: str) -> None:
        self.subject_sha = subject_sha

    def project(self, events: Iterable[RuntimeEvent]) -> dict[str, Any]:
        state: dict[str, Any] = {
            "schema_version": "1.0",
            "subject_sha": self.subject_sha,
            "truth": "NOT_VERIFIED",
            "tasks": {},
            "agents": {},
            "tools": {},
            "policies": {},
            "approvals": {},
            "verifications": {},
            "evidence": {},
        }
        ordered = sorted(events, key=lambda e: (e.timestamp, e.event_id))
        seen: set[str] = set()
        for event in ordered:
            event.validate(self.subject_sha)
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            self._apply(state, event)

        state["event_count"] = len(seen)
        state["projection_digest"] = self.digest(state)
        return state

    def _apply(self, state: dict[str, Any], event: RuntimeEvent) -> None:
        family = event.family
        if family == "task":
            self._upsert(state["tasks"], event.task_id or event.run_id, event)
        elif family == "agent":
            self._upsert(state["agents"], event.agent_id, event)
        elif family == "tool":
            key = event.node_id or event.run_id or event.event_id
            self._upsert(state["tools"], key, event)
        elif family == "policy":
            self._upsert(state["policies"], event.node_id or event.event_id, event)
        elif family == "approval":
            self._upsert(state["approvals"], event.event_id, event)
        elif family == "verification":
            self._upsert(state["verifications"], event.event_id, event)
        elif family == "evidence":
            self._upsert(state["evidence"], event.evidence_id or event.event_id, event)
        else:
            raise ProjectionError(f"unsupported event family: {family}")

        if event.truth_class == "VERIFIED":
            state["truth"] = "VERIFIED"
        elif state["truth"] != "VERIFIED" and event.truth_class in {"OBSERVED", "INFERRED"}:
            state["truth"] = event.truth_class

    @staticmethod
    def _upsert(bucket: dict[str, Any], key: str, event: RuntimeEvent) -> None:
        if not key:
            raise ProjectionError("event missing projection key")
        bucket[key] = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "truth_class": event.truth_class,
            "run_id": event.run_id,
            "node_id": event.node_id,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "input_digest": event.input_digest,
            "output_digest": event.output_digest,
            "evidence_id": event.evidence_id,
            "payload": deepcopy(event.payload),
        }

    @staticmethod
    def digest(state: dict[str, Any]) -> str:
        public = deepcopy(state)
        public.pop("projection_digest", None)
        raw = json.dumps(public, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()
