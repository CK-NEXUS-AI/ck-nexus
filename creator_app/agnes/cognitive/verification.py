"""Verification and PASS contracts for CK-NEXUS components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerificationSubject:
    subject_id: str
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    test_name: str
    passed: bool
    verifier: str
    evidence_ref: str
    subject_id: str
    negative_test: bool = False


@dataclass(frozen=True, slots=True)
class PassResult:
    passed: bool
    reasons: tuple[str, ...]


class PassEngine:
    """Fail-closed PASS evaluator bound to an exact subject."""

    def evaluate(
        self,
        subject: VerificationSubject,
        evidence: tuple[VerificationEvidence, ...],
        *,
        unresolved_blockers: tuple[str, ...] = (),
    ) -> PassResult:
        reasons: list[str] = []
        if not subject.subject_id:
            reasons.append("exact subject is required")
        if not subject.acceptance_criteria:
            reasons.append("acceptance criteria are required")
        if unresolved_blockers:
            reasons.append("unresolved blockers remain")
        if not evidence:
            reasons.append("executed verification evidence is required")
            return PassResult(False, tuple(reasons))

        foreign = [item for item in evidence if item.subject_id != subject.subject_id]
        if foreign:
            reasons.append("evidence is not bound to the exact subject")
        if any(not item.passed for item in evidence):
            reasons.append("one or more verification checks failed")
        if not any(item.negative_test for item in evidence):
            reasons.append("negative/fail-closed test evidence is required")
        if any(not item.verifier or not item.evidence_ref for item in evidence):
            reasons.append("verifier identity and evidence reference are required")

        return PassResult(not reasons, tuple(reasons or ["all PASS contract conditions satisfied"]))
