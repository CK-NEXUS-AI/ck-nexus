from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class ClaimState(str, Enum):
    DISCOVERED = "DISCOVERED"
    PROPOSED = "PROPOSED"
    DISCUSSED = "DISCUSSED"
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class Objection:
    objection_id: str
    claim_id: str
    reason: str
    risk_level: str = "MEDIUM"
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        claim_id: str,
        reason: str,
        risk_level: str = "MEDIUM",
        evidence_refs: tuple[str, ...] = (),
    ) -> "Objection":
        payload = {
            "claim_id": claim_id,
            "reason": reason,
            "risk_level": risk_level,
            "evidence_refs": list(evidence_refs),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return cls(
            objection_id=hashlib.sha256(raw.encode()).hexdigest(),
            claim_id=claim_id,
            reason=reason,
            risk_level=risk_level,
            evidence_refs=tuple(evidence_refs),
        )


@dataclass(slots=True)
class CandidateArtifact:
    candidate_id: str
    cycle_id: str
    producer_id: str
    claim: str
    design: dict[str, Any]
    state: ClaimState = ClaimState.PROPOSED
    objections: list[Objection] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    measurement_digest: str | None = None
    verifier_id: str | None = None
    verification_evidence_digest: str | None = None

    def add_objection(self, objection: Objection) -> None:
        if objection.claim_id != self.candidate_id:
            raise ValueError("objection belongs to a different candidate")
        if all(existing.objection_id != objection.objection_id for existing in self.objections):
            self.objections.append(objection)
        if self.state is ClaimState.PROPOSED:
            self.state = ClaimState.DISCUSSED

    def attach_measurement(self, evidence_refs: list[str]) -> str:
        if not evidence_refs:
            raise ValueError("measurement requires evidence refs")
        self.evidence_refs.extend(ref for ref in evidence_refs if ref not in self.evidence_refs)
        raw = json.dumps(sorted(self.evidence_refs), separators=(",", ":"))
        self.measurement_digest = hashlib.sha256(raw.encode()).hexdigest()
        self.state = ClaimState.MEASURED_NOT_VERIFIED
        return self.measurement_digest

    def attach_independent_verification(self, verifier_id: str, evidence_digest: str) -> None:
        if self.state is not ClaimState.MEASURED_NOT_VERIFIED:
            raise ValueError("candidate must be measured before verification")
        if verifier_id == self.producer_id:
            raise ValueError("self-verification is forbidden")
        if not evidence_digest:
            raise ValueError("verification evidence digest is required")
        self.verifier_id = verifier_id
        self.verification_evidence_digest = evidence_digest
        self.state = ClaimState.VERIFIED

    def reject(self, evidence_ref: str) -> None:
        if evidence_ref and evidence_ref not in self.evidence_refs:
            self.evidence_refs.append(evidence_ref)
        self.state = ClaimState.REJECTED
