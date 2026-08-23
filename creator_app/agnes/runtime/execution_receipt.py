from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


class VerificationState(str, Enum):
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"
    VERIFIED = "VERIFIED"


@dataclass(slots=True)
class ExecutionReceipt:
    execution_id: str
    subject: str
    producer_id: str
    evidence_digest: str
    verifier_id: str | None = None
    verification_evidence_digest: str | None = None

    @property
    def receipt_digest(self) -> str:
        payload = {
            "execution_id": self.execution_id,
            "subject": self.subject,
            "producer_id": self.producer_id,
            "evidence_digest": self.evidence_digest,
            "verifier_id": self.verifier_id,
            "verification_evidence_digest": self.verification_evidence_digest,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def verification_state(self) -> VerificationState:
        if (
            self.verifier_id
            and self.verifier_id != self.producer_id
            and self.verification_evidence_digest
        ):
            return VerificationState.VERIFIED
        return VerificationState.MEASURED_NOT_VERIFIED

    def attach_independent_verification(
        self,
        verifier_id: str,
        verification_evidence_digest: str,
    ) -> None:
        if verifier_id == self.producer_id:
            raise ValueError("self-verification is forbidden")
        if not verification_evidence_digest:
            raise ValueError("verification evidence digest is required")
        self.verifier_id = verifier_id
        self.verification_evidence_digest = verification_evidence_digest
