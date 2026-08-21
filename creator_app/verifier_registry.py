from __future__ import annotations

import json
from dataclasses import dataclass
from time import time
from typing import Protocol


class SignatureVerifier(Protocol):
    def verify(
        self, *, public_key: str, payload: bytes, signature: str
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class VerifierIdentity:
    verifier_id: str
    actor_id: str
    public_key: str
    roles: tuple[str, ...]
    trust_level: str
    valid_from: float
    valid_until: float
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class VerificationArtifact:
    verification_id: str
    verifier_id: str
    subject_digest: str
    policy_digest: str
    task_id: str
    tenant_id: str
    result: str
    issued_at: float
    signature: str


class VerifierRegistry:
    def __init__(self, *, signature_verifier: SignatureVerifier) -> None:
        self._signature_verifier = signature_verifier
        self._identities: dict[str, VerifierIdentity] = {}

    def register(self, identity: VerifierIdentity) -> None:
        if not all(
            value.strip()
            for value in (
                identity.verifier_id,
                identity.actor_id,
                identity.public_key,
                identity.trust_level,
            )
        ):
            raise ValueError("verifier identity fields cannot be empty")
        if identity.valid_until <= identity.valid_from:
            raise ValueError("verifier validity window is invalid")
        self._identities[identity.verifier_id] = identity

    def revoke(self, verifier_id: str) -> None:
        current = self._identities.get(verifier_id)
        if current is None:
            raise KeyError(verifier_id)
        self._identities[verifier_id] = VerifierIdentity(
            verifier_id=current.verifier_id,
            actor_id=current.actor_id,
            public_key=current.public_key,
            roles=current.roles,
            trust_level=current.trust_level,
            valid_from=current.valid_from,
            valid_until=current.valid_until,
            revoked=True,
        )

    def verify(
        self,
        artifact: VerificationArtifact,
        *,
        expected_subject_digest: str,
        expected_policy_digest: str,
        expected_task_id: str,
        expected_tenant_id: str,
        max_age_seconds: int = 900,
    ) -> bool:
        identity = self._identities.get(artifact.verifier_id)
        if identity is None or identity.revoked:
            return False
        now = time()
        if not (identity.valid_from <= artifact.issued_at <= identity.valid_until):
            return False
        if artifact.issued_at > now or now - artifact.issued_at > max_age_seconds:
            return False
        expected = {
            "subject_digest": expected_subject_digest,
            "policy_digest": expected_policy_digest,
            "task_id": expected_task_id,
            "tenant_id": expected_tenant_id,
        }
        for key, value in expected.items():
            if getattr(artifact, key) != value:
                return False
        if artifact.result not in {"PASS", "FAIL"}:
            return False
        return self._signature_verifier.verify(
            public_key=identity.public_key,
            payload=self.signing_payload(artifact),
            signature=artifact.signature,
        )

    @staticmethod
    def signing_payload(artifact: VerificationArtifact) -> bytes:
        payload = {
            "verification_id": artifact.verification_id,
            "verifier_id": artifact.verifier_id,
            "subject_digest": artifact.subject_digest,
            "policy_digest": artifact.policy_digest,
            "task_id": artifact.task_id,
            "tenant_id": artifact.tenant_id,
            "result": artifact.result,
            "issued_at": artifact.issued_at,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
