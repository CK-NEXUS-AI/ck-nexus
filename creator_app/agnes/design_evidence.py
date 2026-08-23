from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DesignEvidenceRecord:
    evidence_id: str
    proposal_id: str
    subject: str
    kind: str
    input_digest: str
    output_digest: str
    policy_decision: str
    verifier: str
    timestamp: str

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        required = {
            "evidence_id": self.evidence_id,
            "proposal_id": self.proposal_id,
            "subject": self.subject,
            "kind": self.kind,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "policy_decision": self.policy_decision,
            "verifier": self.verifier,
            "timestamp": self.timestamp,
        }
        failures.extend(name for name, value in required.items() if not value.strip())
        for name, value in (
            ("input_digest", self.input_digest),
            ("output_digest", self.output_digest),
        ):
            if value and not _is_sha256(value):
                failures.append(f"{name}_must_be_sha256")
        return tuple(failures)


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
