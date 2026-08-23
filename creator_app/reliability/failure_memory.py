"""Append-only failure memory and recurrence protection for CK-NEXUS.

The goal is not to claim software can never fail twice. The enforceable invariant is
stronger and testable: every known failure remains blocked until it has a verified
regression guard, and any recurrence automatically invalidates the prior closure.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class FailureEventType(StrEnum):
    OBSERVED = "observed"
    PROTECTED = "protected"


class FailureState(StrEnum):
    UNKNOWN = "unknown"
    BLOCKED_UNPROTECTED = "blocked_unprotected"
    PROTECTED = "protected"
    BLOCKED_RECURRENCE = "blocked_recurrence"


_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "authorization:",
    "password=",
    "passwd=",
    "api_key=",
    "apikey=",
    "client_secret=",
)
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_HEX_RE = re.compile(r"\b[0-9a-f]{8,64}\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\b\d+\b")
_WS_RE = re.compile(r"\s+")


def _require_non_secret(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    lowered = normalized.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise ValueError(f"{field_name} appears to contain secret material")
    return normalized


def normalize_failure_signature(signature: str) -> str:
    """Normalize safe/redacted error text into a stable recurrence signature.

    Dynamic UUIDs, long hexadecimal identifiers and decimal numbers are replaced so
    retries of the same defect fingerprint together. The caller must supply already
    redacted text; obvious secret markers are rejected fail-closed.
    """

    value = _require_non_secret(signature, "signature").lower()
    value = _UUID_RE.sub("<uuid>", value)
    value = _HEX_RE.sub("<hex>", value)
    value = _NUMBER_RE.sub("<n>", value)
    return _WS_RE.sub(" ", value).strip()


def fingerprint_failure(
    *,
    component: str,
    operation: str,
    error_type: str,
    safe_signature: str,
) -> str:
    component = _require_non_secret(component, "component")
    operation = _require_non_secret(operation, "operation")
    error_type = _require_non_secret(error_type, "error_type")
    signature = normalize_failure_signature(safe_signature)
    canonical = "\x1f".join(
        (component.lower(), operation.lower(), error_type.lower(), signature)
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class FailureObservation:
    component: str
    operation: str
    error_type: str
    safe_signature: str
    subject_sha: str
    evidence_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "component",
            "operation",
            "error_type",
            "safe_signature",
            "subject_sha",
            "evidence_digest",
        ):
            _require_non_secret(str(getattr(self, field_name)), field_name)

    @property
    def fingerprint(self) -> str:
        return fingerprint_failure(
            component=self.component,
            operation=self.operation,
            error_type=self.error_type,
            safe_signature=self.safe_signature,
        )


@dataclass(frozen=True, slots=True)
class FailureProtection:
    root_cause: str
    fix_ref: str
    regression_test_id: str
    verifier_id: str
    verified_subject_sha: str
    proof_digest: str

    def __post_init__(self) -> None:
        for field_name in (
            "root_cause",
            "fix_ref",
            "regression_test_id",
            "verifier_id",
            "verified_subject_sha",
            "proof_digest",
        ):
            _require_non_secret(str(getattr(self, field_name)), field_name)


@dataclass(frozen=True, slots=True)
class FailureEvent:
    sequence: int
    event_type: FailureEventType
    fingerprint: str
    recorded_at: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FailureDecision:
    fingerprint: str
    state: FailureState
    occurrence_count: int
    recurrence_count: int
    release_blocked: bool
    reason: str


class FailureLedger:
    """Append-only machine-readable memory of failures and verified protections."""

    def __init__(self, events: tuple[FailureEvent, ...] = ()) -> None:
        self._events: list[FailureEvent] = []
        for event in events:
            self._append_validated(event)

    @property
    def events(self) -> tuple[FailureEvent, ...]:
        return tuple(self._events)

    def observe(self, observation: FailureObservation) -> FailureDecision:
        fingerprint = observation.fingerprint
        self._append(
            FailureEventType.OBSERVED,
            fingerprint,
            {
                "component": observation.component,
                "operation": observation.operation,
                "error_type": observation.error_type,
                "normalized_signature": normalize_failure_signature(
                    observation.safe_signature
                ),
                "subject_sha": observation.subject_sha,
                "evidence_digest": observation.evidence_digest,
            },
        )
        return self.decision(fingerprint)

    def protect(self, fingerprint: str, protection: FailureProtection) -> FailureDecision:
        if not self._observations(fingerprint):
            raise ValueError("cannot protect an unknown failure fingerprint")
        self._append(
            FailureEventType.PROTECTED,
            fingerprint,
            asdict(protection),
        )
        return self.decision(fingerprint)

    def decision(self, fingerprint: str) -> FailureDecision:
        observations = self._observations(fingerprint)
        protections = self._protections(fingerprint)
        if not observations:
            return FailureDecision(
                fingerprint=fingerprint,
                state=FailureState.UNKNOWN,
                occurrence_count=0,
                recurrence_count=0,
                release_blocked=False,
                reason="failure fingerprint has not been observed",
            )

        last_observation_sequence = observations[-1].sequence
        last_protection_sequence = protections[-1].sequence if protections else 0
        occurrence_count = len(observations)
        recurrence_count = max(0, occurrence_count - 1)

        if not protections:
            state = FailureState.BLOCKED_UNPROTECTED
            reason = "known failure has no verified regression protection"
        elif last_observation_sequence > last_protection_sequence:
            state = FailureState.BLOCKED_RECURRENCE
            reason = "known failure recurred after protection and must be re-verified"
        else:
            state = FailureState.PROTECTED
            reason = "latest occurrence has verified regression protection"

        return FailureDecision(
            fingerprint=fingerprint,
            state=state,
            occurrence_count=occurrence_count,
            recurrence_count=recurrence_count,
            release_blocked=state is not FailureState.PROTECTED,
            reason=reason,
        )

    def all_decisions(self) -> tuple[FailureDecision, ...]:
        fingerprints = sorted({event.fingerprint for event in self._events})
        return tuple(self.decision(fingerprint) for fingerprint in fingerprints)

    def release_blockers(self) -> tuple[FailureDecision, ...]:
        return tuple(decision for decision in self.all_decisions() if decision.release_blocked)

    def to_jsonl(self) -> str:
        lines = []
        for event in self._events:
            lines.append(
                json.dumps(
                    {
                        "sequence": event.sequence,
                        "event_type": event.event_type.value,
                        "fingerprint": event.fingerprint,
                        "recorded_at": event.recorded_at,
                        "payload": event.payload,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        return "\n".join(lines) + ("\n" if lines else "")

    @classmethod
    def from_jsonl(cls, content: str) -> FailureLedger:
        events: list[FailureEvent] = []
        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            if not raw_line.strip():
                continue
            try:
                item = json.loads(raw_line)
                event = FailureEvent(
                    sequence=int(item["sequence"]),
                    event_type=FailureEventType(item["event_type"]),
                    fingerprint=str(item["fingerprint"]),
                    recorded_at=str(item["recorded_at"]),
                    payload=dict(item["payload"]),
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid failure ledger line {line_number}") from exc
            events.append(event)
        return cls(tuple(events))

    def _observations(self, fingerprint: str) -> list[FailureEvent]:
        return [
            event
            for event in self._events
            if event.fingerprint == fingerprint
            and event.event_type is FailureEventType.OBSERVED
        ]

    def _protections(self, fingerprint: str) -> list[FailureEvent]:
        return [
            event
            for event in self._events
            if event.fingerprint == fingerprint
            and event.event_type is FailureEventType.PROTECTED
        ]

    def _append(
        self,
        event_type: FailureEventType,
        fingerprint: str,
        payload: dict[str, Any],
    ) -> None:
        event = FailureEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            fingerprint=fingerprint,
            recorded_at=datetime.now(UTC).isoformat(),
            payload=payload,
        )
        self._append_validated(event)

    def _append_validated(self, event: FailureEvent) -> None:
        expected_sequence = len(self._events) + 1
        if event.sequence != expected_sequence:
            raise ValueError("failure ledger sequence must be contiguous and append-only")
        if not re.fullmatch(r"[0-9a-f]{64}", event.fingerprint):
            raise ValueError("failure fingerprint must be a lowercase SHA-256 digest")
        _require_non_secret(event.recorded_at, "recorded_at")

        required_fields = {
            FailureEventType.OBSERVED: (
                "component", "operation", "error_type", "normalized_signature",
                "subject_sha", "evidence_digest",
            ),
            FailureEventType.PROTECTED: (
                "root_cause", "fix_ref", "regression_test_id", "verifier_id",
                "verified_subject_sha", "proof_digest",
            ),
        }[event.event_type]
        missing = [field for field in required_fields if field not in event.payload]
        if missing:
            raise ValueError(
                f"{event.event_type.value} failure event missing required payload fields: "
                + ", ".join(missing)
            )
        for field in required_fields:
            value = event.payload[field]
            if not isinstance(value, str):
                raise ValueError(f"failure event payload field {field} must be a string")
            _require_non_secret(value, field)

        if event.event_type is FailureEventType.OBSERVED:
            normalized_signature = normalize_failure_signature(
                event.payload["normalized_signature"]
            )
            if event.payload["normalized_signature"] != normalized_signature:
                raise ValueError("observed normalized_signature must be canonical")
            expected_fingerprint = fingerprint_failure(
                component=event.payload["component"],
                operation=event.payload["operation"],
                error_type=event.payload["error_type"],
                safe_signature=normalized_signature,
            )
            if event.fingerprint != expected_fingerprint:
                raise ValueError("observed failure fingerprint does not match payload")

        if event.event_type is FailureEventType.PROTECTED and not self._observations(
            event.fingerprint
        ):
            raise ValueError("cannot replay protection before a matching failure observation")

        encoded_payload = json.dumps(event.payload, sort_keys=True, default=str)
        _require_non_secret(encoded_payload, "payload")
        self._events.append(event)
