import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from creator_app.agnes.execution.omni import EvidenceLevel
from creator_app.agnes.execution.omni_provider import (
    DurableExecutionReplayStore,
    OmniAuthorityUnavailable,
    OmniProviderAdapter,
)
from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest
from creator_app.council_authority.omni_issuer import (
    Ed25519OmniIssuer,
    Ed25519OmniProofVerifier,
    OmniCapabilityRule,
    OmniIssuanceDenied,
    SQLiteOmniIssuerStore,
)


def request(execution_id="issuer-exec-1", *, environment="development", capability="code.read"):
    return SkillExecutionRequest(
        execution_id=execution_id,
        correlation_id="corr-issuer",
        skill_id="repo.inspect",
        skill_version="1",
        executor=ExecutorType.INTERNAL,
        goal="inspect repository",
        plan_step={"tool_id": "repo.read", "target_id": "repo:ck-nexus"},
        environment=environment,
        granted_capabilities=(capability,),
    )


def issuer(tmp_path, *, risk=EvidenceLevel.E1, evidence=True, approval=None):
    return Ed25519OmniIssuer(
        private_key=Ed25519PrivateKey.generate(),
        store=SQLiteOmniIssuerStore(tmp_path / "issuer.sqlite"),
        issuer_id="cknexus-omni-issuer-test",
        agent_id="agnes-agent",
        model_id="qwen-test",
        policy_id="repo-read-policy-v1",
        rules=(
            OmniCapabilityRule(
                "repo.inspect",
                "code.read",
                "repo.read",
                "repo:ck-nexus",
                ("development", "test", "staging", "production"),
                risk,
                True,
            ),
        ),
        runtime_id="agnes-runtime-test",
        verifier_id="evidence-verifier-test",
        evidence_verifier=(lambda _request, _context: True) if evidence else None,
        approval_verifier=approval,
    )


def test_real_ed25519_issuer_runs_through_adapter_once(tmp_path):
    auth = issuer(tmp_path)
    req = request()
    adapter = OmniProviderAdapter(auth, DurableExecutionReplayStore(tmp_path / "replay.sqlite"))
    ctx = adapter(req)
    assert ctx.proof
    assert Ed25519OmniProofVerifier(auth.public_key, issuer_id=auth.issuer_id).verify(req, ctx)
    with pytest.raises(OmniAuthorityUnavailable):
        adapter(req)


def test_signature_binds_inputs_tool_target_and_lease(tmp_path):
    auth = issuer(tmp_path)
    req = request()
    ctx = auth.issue_context(req)
    verifier = Ed25519OmniProofVerifier(auth.public_key, issuer_id=auth.issuer_id)
    assert verifier.verify(req, ctx)
    assert not verifier.verify(replace(req, inputs={"path": "other"}), ctx)
    assert not verifier.verify(
        replace(req, plan_step={"tool_id": "repo.write", "target_id": "repo:ck-nexus"}), ctx
    )
    assert not verifier.verify(req, replace(ctx, target_id="repo:other"))
    assert not verifier.verify(req, replace(ctx, lease=replace(ctx.lease, lease_id="forged-lease")))
    assert not verifier.verify(
        req, replace(ctx, proof=ctx.proof[:-1] + ("A" if ctx.proof[-1] != "A" else "B"))
    )


def test_policy_mismatch_and_production_non_readonly_fail_closed(tmp_path):
    auth = issuer(tmp_path, risk=EvidenceLevel.E1)
    with pytest.raises(OmniIssuanceDenied, match="no_matching"):
        auth.issue_context(request(environment="production"))
    with pytest.raises(OmniIssuanceDenied, match="no_matching"):
        auth.issue_context(request(capability="code.write"))


def test_evidence_and_approval_fail_closed(tmp_path):
    auth = issuer(tmp_path, evidence=False)
    with pytest.raises(OmniAuthorityUnavailable, match="execution_evidence_invalid_or_missing"):
        OmniProviderAdapter(auth, DurableExecutionReplayStore(tmp_path / "replay.sqlite"))(
            request()
        )
    approval_auth = issuer(tmp_path / "approval", approval=lambda _request: False)
    approved_req = replace(
        request("approval-exec"), requires_approval=True, approval_id="approval-1"
    )
    with pytest.raises(OmniIssuanceDenied, match="approval_invalid"):
        approval_auth.issue_context(approved_req)


def test_revocation_is_persistent_and_atomic_consume_checks_it(tmp_path):
    auth = issuer(tmp_path)
    req = request()
    ctx = auth.issue_context(req)
    assert auth.revoke_lease(ctx.lease.lease_id)
    assert auth.is_lease_revoked(ctx.lease.lease_id)
    reopened = SQLiteOmniIssuerStore(tmp_path / "issuer.sqlite")
    assert reopened.is_revoked(ctx.lease.lease_id)
    from creator_app.agnes.execution.omni_provider import execution_binding_sha256

    assert not auth.consume_execution(
        req.execution_id, execution_binding_sha256(req, ctx), ctx.lease.lease_id
    )


def test_authority_atomic_consume_only_once_under_concurrency(tmp_path):
    auth = issuer(tmp_path)
    req = request()
    ctx = auth.issue_context(req)
    from creator_app.agnes.execution.omni_provider import execution_binding_sha256

    binding = execution_binding_sha256(req, ctx)
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(
            pool.map(
                lambda _: auth.consume_execution(req.execution_id, binding, ctx.lease.lease_id),
                range(32),
            )
        )
    assert sum(results) == 1


def test_expired_lease_fails_closed(tmp_path):
    auth = issuer(tmp_path)
    auth.lease_ttl_seconds = 1
    req = request()
    ctx = auth.issue_context(req)
    time.sleep(1.1)
    assert auth.is_lease_revoked(ctx.lease.lease_id)
    reopened = SQLiteOmniIssuerStore(tmp_path / "issuer.sqlite")
    assert reopened.is_revoked(ctx.lease.lease_id)
    from creator_app.agnes.execution.omni_provider import execution_binding_sha256

    assert not auth.consume_execution(
        req.execution_id, execution_binding_sha256(req, ctx), ctx.lease.lease_id
    )
