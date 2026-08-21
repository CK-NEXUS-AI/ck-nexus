from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class FormalLanguage(StrEnum):
    LEAN4 = "lean4"
    SMTLIB2 = "smtlib2"
    TLA_PLUS = "tla_plus"
    OTHER = "other"


class ProofResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class FormalInvariant(BaseModel):
    invariant_id: str
    subject_digest: str
    statement_digest: str
    critical: bool = True


class ProofReceipt(BaseModel):
    invariant_id: str
    subject_digest: str
    language: FormalLanguage
    checker_id: str
    checker_version: str
    theorem_digest: str
    proof_digest: str
    result: ProofResult
    deterministic: bool = True
    network_used: bool = False
    evidence_ids: tuple[str, ...] = ()


class FormalVerificationDecision(BaseModel):
    invariant_id: str
    verified: bool
    reason: str
    evidence_ids: tuple[str, ...] = ()
    production_activation_allowed: bool = False


class FormalVerificationPolicy(BaseModel):
    require_deterministic_checker: bool = True
    require_network_off: bool = True

    def verify(
        self,
        invariant: FormalInvariant,
        receipt: ProofReceipt,
    ) -> FormalVerificationDecision:
        if receipt.invariant_id != invariant.invariant_id:
            return self._deny(invariant, receipt, "invariant_identity_mismatch")
        if receipt.subject_digest != invariant.subject_digest:
            return self._deny(invariant, receipt, "subject_digest_mismatch")
        if not receipt.checker_id.strip() or not receipt.checker_version.strip():
            return self._deny(invariant, receipt, "checker_identity_missing")
        if receipt.checker_version.strip().lower() in {"latest", "main", "head"}:
            return self._deny(invariant, receipt, "checker_version_not_pinned")
        if self.require_deterministic_checker and not receipt.deterministic:
            return self._deny(invariant, receipt, "checker_not_deterministic")
        if self.require_network_off and receipt.network_used:
            return self._deny(invariant, receipt, "networked_proof_not_allowed")
        if not receipt.evidence_ids:
            return self._deny(invariant, receipt, "proof_evidence_missing")
        if receipt.result != ProofResult.PASS:
            return self._deny(invariant, receipt, f"proof_result_{receipt.result.value}")
        if not receipt.theorem_digest or not receipt.proof_digest:
            return self._deny(invariant, receipt, "proof_artifact_digest_missing")
        return FormalVerificationDecision(
            invariant_id=invariant.invariant_id,
            verified=True,
            reason="machine_verification_passed",
            evidence_ids=receipt.evidence_ids,
            production_activation_allowed=False,
        )

    @staticmethod
    def _deny(
        invariant: FormalInvariant,
        receipt: ProofReceipt,
        reason: str,
    ) -> FormalVerificationDecision:
        return FormalVerificationDecision(
            invariant_id=invariant.invariant_id,
            verified=False,
            reason=reason,
            evidence_ids=receipt.evidence_ids,
            production_activation_allowed=False,
        )
