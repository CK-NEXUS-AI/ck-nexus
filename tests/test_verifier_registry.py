from __future__ import annotations

import hashlib
import hmac
from time import time

from creator_app.verifier_registry import (
    VerificationArtifact,
    VerifierIdentity,
    VerifierRegistry,
)


class FakeSignatureVerifier:
    def verify(self, *, public_key: str, payload: bytes, signature: str) -> bool:
        expected = hmac.new(public_key.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def make_identity() -> VerifierIdentity:
    now = time()
    return VerifierIdentity(
        verifier_id="verifier-1",
        actor_id="human-1",
        public_key="test-public-key",
        roles=("security",),
        trust_level="trusted",
        valid_from=now - 60,
        valid_until=now + 3600,
    )


def make_artifact(*, task_id: str = "task-1", signing_key: str = "test-public-key"):
    base = VerificationArtifact(
        verification_id="verification-1",
        verifier_id="verifier-1",
        subject_digest="s" * 64,
        policy_digest="p" * 64,
        task_id=task_id,
        tenant_id="tenant-1",
        result="PASS",
        issued_at=time(),
        signature="",
    )
    signature = hmac.new(
        signing_key.encode(),
        VerifierRegistry.signing_payload(base),
        hashlib.sha256,
    ).hexdigest()
    return VerificationArtifact(
        verification_id=base.verification_id,
        verifier_id=base.verifier_id,
        subject_digest=base.subject_digest,
        policy_digest=base.policy_digest,
        task_id=base.task_id,
        tenant_id=base.tenant_id,
        result=base.result,
        issued_at=base.issued_at,
        signature=signature,
    )


def registry() -> VerifierRegistry:
    value = VerifierRegistry(signature_verifier=FakeSignatureVerifier())
    value.register(make_identity())
    return value


def verify(value: VerifierRegistry, artifact: VerificationArtifact) -> bool:
    return value.verify(
        artifact,
        expected_subject_digest="s" * 64,
        expected_policy_digest="p" * 64,
        expected_task_id="task-1",
        expected_tenant_id="tenant-1",
    )


def test_signed_verification_is_accepted() -> None:
    assert verify(registry(), make_artifact()) is True


def test_tampered_scope_is_rejected() -> None:
    assert verify(registry(), make_artifact(task_id="task-other")) is False


def test_wrong_signer_is_rejected() -> None:
    assert verify(registry(), make_artifact(signing_key="attacker")) is False


def test_revoked_verifier_is_rejected() -> None:
    value = registry()
    artifact = make_artifact()
    value.revoke("verifier-1")
    assert verify(value, artifact) is False
