from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .subject import SubjectComponent, VerificationSubject


class GapStatus(StrEnum):
    NEW_SUBJECT = "NEW_SUBJECT"
    SUBJECT_CHANGED = "SUBJECT_CHANGED"
    RESUME_EXACT_SUBJECT = "RESUME_EXACT_SUBJECT"
    RERUN_STALE_EVIDENCE = "RERUN_STALE_EVIDENCE"
    BLOCK_INVALID_LEDGER = "BLOCK_INVALID_LEDGER"
    BLOCK_VERIFIER_SEPARATION = "BLOCK_VERIFIER_SEPARATION"
    REUSE_EXACT_SUBJECT = "REUSE_EXACT_SUBJECT"


class VerificationScope(StrEnum):
    SOURCE_INTEGRITY = "SOURCE_INTEGRITY"
    Q10_SECURITY = "Q10_SECURITY"
    Q11_PROVIDER_CREDENTIAL_FAULT = "Q11_PROVIDER_CREDENTIAL_FAULT"
    Q12_SANDBOX = "Q12_SANDBOX"
    PROVENANCE = "PROVENANCE"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    FINAL_REPORT = "FINAL_REPORT"


ALL_SCOPES = tuple(VerificationScope)


@dataclass(frozen=True, slots=True)
class GapDecision:
    status: GapStatus
    current_subject_id: str
    current_subject_digest: str
    changed_components: tuple[SubjectComponent, ...]
    rerun_scopes: tuple[VerificationScope, ...]
    authoritative_reuse_allowed: bool
    historical_reference_allowed: bool
    reasons: tuple[str, ...]


class SubjectGapAnalyzer:
    """Fail-closed reuse/resume logic for Verifier Pro evidence.

    Evidence may be authoritatively reused only when the full verification
    subject is byte-for-byte identical, the ledger verifies, evidence is fresh,
    required coverage is complete, and producer/verifier separation still holds.

    When any subject component changes, prior evidence remains useful only as an
    explicitly old-subject historical reference. It must never be rebound to the
    new subject or presented as fresh evidence for that subject.
    """

    def assess(
        self,
        *,
        current: VerificationSubject,
        previous: VerificationSubject | None,
        ledger_valid: bool,
        evidence_complete: bool,
        evidence_fresh: bool,
        verifier_separation_valid: bool,
    ) -> GapDecision:
        current.validate()

        if previous is None:
            return GapDecision(
                status=GapStatus.NEW_SUBJECT,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=tuple(SubjectComponent),
                rerun_scopes=ALL_SCOPES,
                authoritative_reuse_allowed=False,
                historical_reference_allowed=False,
                reasons=("no prior subject exists",),
            )

        previous.validate()
        changed = tuple(sorted(current.changed_components(previous), key=lambda item: item.value))
        if changed:
            return GapDecision(
                status=GapStatus.SUBJECT_CHANGED,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=changed,
                rerun_scopes=ALL_SCOPES,
                authoritative_reuse_allowed=False,
                historical_reference_allowed=True,
                reasons=(
                    "verification subject changed",
                    "old evidence remains bound to the old subject",
                    "authoritative evidence must be regenerated for the new subject",
                ),
            )

        if not ledger_valid:
            return GapDecision(
                status=GapStatus.BLOCK_INVALID_LEDGER,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=(),
                rerun_scopes=(),
                authoritative_reuse_allowed=False,
                historical_reference_allowed=False,
                reasons=("append-only evidence ledger integrity failed",),
            )

        if not verifier_separation_valid:
            return GapDecision(
                status=GapStatus.BLOCK_VERIFIER_SEPARATION,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=(),
                rerun_scopes=(VerificationScope.INDEPENDENT_VERIFICATION,),
                authoritative_reuse_allowed=False,
                historical_reference_allowed=True,
                reasons=("producer/verifier separation is not valid",),
            )

        if not evidence_complete:
            return GapDecision(
                status=GapStatus.RESUME_EXACT_SUBJECT,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=(),
                rerun_scopes=ALL_SCOPES,
                authoritative_reuse_allowed=False,
                historical_reference_allowed=True,
                reasons=("exact subject found but required evidence coverage is incomplete",),
            )

        if not evidence_fresh:
            return GapDecision(
                status=GapStatus.RERUN_STALE_EVIDENCE,
                current_subject_id=current.subject_id,
                current_subject_digest=current.digest,
                changed_components=(),
                rerun_scopes=ALL_SCOPES,
                authoritative_reuse_allowed=False,
                historical_reference_allowed=True,
                reasons=("exact-subject evidence exists but is stale under freshness policy",),
            )

        return GapDecision(
            status=GapStatus.REUSE_EXACT_SUBJECT,
            current_subject_id=current.subject_id,
            current_subject_digest=current.digest,
            changed_components=(),
            rerun_scopes=(),
            authoritative_reuse_allowed=True,
            historical_reference_allowed=True,
            reasons=("exact subject, valid ledger, complete fresh evidence and valid verifier separation",),
        )
