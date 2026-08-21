"""Zero-trust contracts for cognitive dependencies."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class TrustState(StrEnum):
    UNKNOWN = "unknown"
    QUARANTINED = "quarantined"
    SCANNED = "scanned"
    SANDBOXED = "sandboxed"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    REVOKED = "revoked"


_ORDER = {
    TrustState.UNKNOWN: 0,
    TrustState.QUARANTINED: 1,
    TrustState.SCANNED: 2,
    TrustState.SANDBOXED: 3,
    TrustState.VERIFIED: 4,
    TrustState.TRUSTED: 5,
}


@dataclass(frozen=True, slots=True)
class TrustRecord:
    subject_id: str
    subject_type: str
    state: TrustState = TrustState.UNKNOWN
    evidence_refs: tuple[str, ...] = ()


class TrustEngine:
    """Monotonic trust promotion; revocation is always allowed."""

    def transition(
        self,
        record: TrustRecord,
        target: TrustState,
        *,
        evidence_ref: str | None = None,
    ) -> TrustRecord:
        if target is TrustState.REVOKED:
            refs = record.evidence_refs + ((evidence_ref,) if evidence_ref else ())
            return replace(record, state=target, evidence_refs=refs)
        if record.state is TrustState.REVOKED:
            raise ValueError("revoked trust must be re-onboarded as a new subject/version")
        if target not in _ORDER:
            raise ValueError("invalid trust target")
        if _ORDER[target] != _ORDER[record.state] + 1:
            raise ValueError("trust promotion must proceed one verified stage at a time")
        if target in {TrustState.SCANNED, TrustState.SANDBOXED, TrustState.VERIFIED, TrustState.TRUSTED} and not evidence_ref:
            raise ValueError("evidence_ref is required for trust promotion")
        refs = record.evidence_refs + ((evidence_ref,) if evidence_ref else ())
        return replace(record, state=target, evidence_refs=refs)

    @staticmethod
    def may_execute(record: TrustRecord) -> bool:
        return record.state in {TrustState.VERIFIED, TrustState.TRUSTED}
