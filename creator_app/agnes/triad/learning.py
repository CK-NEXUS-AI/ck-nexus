from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class LearningKind(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    STRATEGY = "STRATEGY"
    CAPABILITY = "CAPABILITY"


class LearningState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    TESTED = "TESTED"
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class LearningCandidate:
    learning_id: str
    kind: LearningKind
    summary: str
    source_refs: list[str] = field(default_factory=list)
    state: LearningState = LearningState.DISCOVERED
    measurement_refs: list[str] = field(default_factory=list)
    producer_id: str = "triad"
    verifier_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        kind: LearningKind,
        summary: str,
        source_refs: list[str] | None = None,
        producer_id: str = "triad",
    ) -> "LearningCandidate":
        refs = list(source_refs or [])
        payload = {"kind": kind.value, "summary": summary, "source_refs": sorted(refs)}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return cls(hashlib.sha256(raw.encode()).hexdigest(), kind, summary, refs, producer_id=producer_id)

    def quarantine(self) -> None:
        if self.state is not LearningState.DISCOVERED:
            raise ValueError("only discovered learning can be quarantined")
        self.state = LearningState.QUARANTINED

    def mark_tested(self) -> None:
        if self.state is not LearningState.QUARANTINED:
            raise ValueError("learning must be quarantined before testing")
        self.state = LearningState.TESTED

    def attach_measurement(self, refs: list[str]) -> None:
        if self.state is not LearningState.TESTED:
            raise ValueError("learning must be tested before measurement")
        if not refs:
            raise ValueError("measurement evidence is required")
        self.measurement_refs.extend(ref for ref in refs if ref not in self.measurement_refs)
        self.state = LearningState.MEASURED_NOT_VERIFIED

    def attach_independent_verification(self, verifier_id: str) -> None:
        if self.state is not LearningState.MEASURED_NOT_VERIFIED:
            raise ValueError("learning must be measured before verification")
        if verifier_id == self.producer_id:
            raise ValueError("self-verification is forbidden")
        self.verifier_id = verifier_id
        self.state = LearningState.VERIFIED

    def reject(self) -> None:
        self.state = LearningState.REJECTED


@dataclass(slots=True)
class LearningConsolidator:
    candidates: dict[str, LearningCandidate] = field(default_factory=dict)

    def add(self, candidate: LearningCandidate) -> bool:
        if candidate.learning_id in self.candidates:
            return False
        self.candidates[candidate.learning_id] = candidate
        return True

    def verified(self) -> tuple[LearningCandidate, ...]:
        return tuple(c for c in self.candidates.values() if c.state is LearningState.VERIFIED)

    def pending(self) -> tuple[LearningCandidate, ...]:
        return tuple(
            c for c in self.candidates.values()
            if c.state not in {LearningState.VERIFIED, LearningState.REJECTED}
        )
