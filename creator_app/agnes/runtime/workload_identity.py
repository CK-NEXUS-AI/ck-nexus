from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json


@dataclass(frozen=True, slots=True)
class WorkloadIdentity:
    subject: str
    node_id: str
    process_id: int
    runtime: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    attestation_evidence_digest: str | None = None

    @property
    def identity_digest(self) -> str:
        payload = {
            "subject": self.subject,
            "node_id": self.node_id,
            "process_id": self.process_id,
            "runtime": self.runtime,
            "capabilities": sorted(self.capabilities),
            "attestation_evidence_digest": self.attestation_evidence_digest,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def attested(self) -> bool:
        return bool(self.attestation_evidence_digest)
