from __future__ import annotations

import time
from dataclasses import replace

import pytest

from creator_app.agnes.execution.omni import (
    AgentIdentity,
    CapabilityLease,
    DelegationContext,
    EvidenceLevel,
    OMNIExecutionContext,
    OmniGateError,
    PreExecutionRiskVerdict,
    RiskDecision,
)
from creator_app.agnes.execution.omni_provider import (
    DurableExecutionReplayStore,
    OmniAuthorityUnavailable,
    OmniProviderAdapter,
    execution_binding_sha256,
)
from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest


def request():
    return SkillExecutionRequest(
        execution_id="exec-provider-1",
        correlation_id="corr-1",
        skill_id="brain.plan",
        skill_version="1",
        executor=ExecutorType.INTERNAL,
        goal="test",
        plan_step={"tool_id": "repo.read", "target_id": "repo:ck-nexus"},
        granted_capabilities=("code.read",),
    )


def context(req=None, **changes):
    req = req or request()
    now = time.time()
    value = OMNIExecutionContext(
        identity=AgentIdentity("agent-1", "model-1", "external-omni", "proof:agent-1"),
        capability_id="code.read",
        lease=CapabilityLease("lease-1", "agent-1", ("code.read",), now - 1, now + 60),
        policy_id="policy-1",
        risk_verdict=PreExecutionRiskVerdict(
            "risk-1",
            req.execution_id,
            "agent-1",
            "code.read",
            "policy-1",
            RiskDecision.ALLOW,
            EvidenceLevel.E1,
            "LOCAL",
            "reversible",
            "none",
            False,
        ),
        tool_id="repo.read",
        target_id="repo:ck-nexus",
        runtime_id="runtime-1",
        verifier_id="verifier-1",
        evidence_required=True,
        intent_id="intent-1",
    )
    return replace(value, **changes)


class FakeIndependentAuthority:
    def __init__(
        self, ctx=None, *, proof=True, evidence=True, revoked=False, consume=True, failure=None
    ):
        self.ctx = ctx
        self.proof = proof
        self.evidence = evidence
        self.revoked = revoked
        self.consume = consume
        self.failure = failure
        self.consumed = []
        self.revocation_checks = 0

    def issue_context(self, req):
        if self.failure:
            raise self.failure
        return self.ctx or context(req)

    def verify_context_proof(self, req, ctx):
        return self.proof

    def verify_evidence(self, req, ctx):
        return self.evidence

    def is_lease_revoked(self, lease_id):
        self.revocation_checks += 1
        return self.revoked

    def consume_execution(self, execution_id, binding_sha256, lease_id):
        self.consumed.append((execution_id, binding_sha256, lease_id))
        return self.consume


def test_missing_provider_fails_closed(tmp_path):
    with pytest.raises(OmniAuthorityUnavailable, match="not_configured"):
        OmniProviderAdapter(replay_store=DurableExecutionReplayStore(tmp_path / "replay.sqlite"))(
            request()
        )


def test_valid_authority_context_is_accepted_once(tmp_path):
    req = request()
    authority = FakeIndependentAuthority()
    result = OmniProviderAdapter(
        authority, DurableExecutionReplayStore(tmp_path / "replay.sqlite")
    )(req)
    assert result.risk_verdict.execution_id == req.execution_id
    assert authority.consumed == [
        (req.execution_id, execution_binding_sha256(req, result), result.lease.lease_id)
    ]
    assert authority.revocation_checks == 2


@pytest.mark.parametrize(
    "case",
    [
        "expired",
        "revoked-in-context",
        "scope",
        "wrong-execution",
        "wrong-tool",
        "wrong-target",
        "bad-signature",
        "missing-evidence",
        "revoked-authority",
        "replay",
        "provider-error",
    ],
)
def test_provider_negative_cases_fail_closed(case, tmp_path):
    req = request()
    ctx = context(req)
    kwargs = {}
    if case == "expired":
        kwargs["ctx"] = replace(
            ctx,
            lease=CapabilityLease(
                "lease-1", "agent-1", ("code.read",), time.time() - 100, time.time() - 1
            ),
        )
    elif case == "revoked-in-context":
        kwargs["ctx"] = replace(ctx, lease=replace(ctx.lease, revocation_ref="revoked"))
    elif case == "scope":
        kwargs["ctx"] = replace(ctx, capability_id="code.write")
    elif case == "wrong-execution":
        kwargs["ctx"] = replace(
            ctx, risk_verdict=replace(ctx.risk_verdict, execution_id="other-exec")
        )
    elif case == "wrong-tool":
        kwargs["ctx"] = replace(ctx, tool_id="repo.write")
    elif case == "wrong-target":
        kwargs["ctx"] = replace(ctx, target_id="repo:other")
    elif case == "bad-signature":
        kwargs["proof"] = False
    elif case == "missing-evidence":
        kwargs["evidence"] = False
    elif case == "revoked-authority":
        kwargs["revoked"] = True
    elif case == "replay":
        kwargs["consume"] = False
    elif case == "provider-error":
        kwargs["failure"] = RuntimeError("authority offline")
    with pytest.raises((OmniGateError, OmniAuthorityUnavailable)):
        OmniProviderAdapter(
            FakeIndependentAuthority(**kwargs),
            DurableExecutionReplayStore(tmp_path / (case + ".sqlite")),
        )(req)


def test_request_missing_tool_or_target_fails_closed_before_authority(tmp_path):
    req = replace(request(), plan_step={"tool_id": "repo.read"})
    authority = FakeIndependentAuthority()
    with pytest.raises(OmniGateError, match="target_binding_missing"):
        OmniProviderAdapter(authority, DurableExecutionReplayStore(tmp_path / "replay.sqlite"))(req)
    assert not authority.consumed


def test_replay_store_persists_across_reopen(tmp_path):
    path = tmp_path / "replay.sqlite"
    assert DurableExecutionReplayStore(path).consume_once("exec-restart")
    assert not DurableExecutionReplayStore(path).consume_once("exec-restart")


def test_replay_store_atomic_under_concurrency(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "replay.sqlite"

    def consume(_):
        return DurableExecutionReplayStore(path).consume_once("exec-race")

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(consume, range(64)))
    assert sum(results) == 1


def test_adapter_requires_durable_store(tmp_path):
    with pytest.raises(OmniAuthorityUnavailable, match="durable_replay_store_not_configured"):
        OmniProviderAdapter(FakeIndependentAuthority())(request())


def test_execution_binding_changes_when_inputs_or_tool_target_change():
    req = request()
    ctx = context(req)
    original = execution_binding_sha256(req, ctx)
    changed_inputs = replace(req, inputs={"path": "different"})
    changed_tool = replace(ctx, tool_id="repo.write")
    changed_timeout = replace(req, timeout_seconds=req.timeout_seconds + 1)
    delegated = replace(
        ctx,
        delegation=DelegationContext(
            "parent-exec", "parent-agent", ("code.read",), ctx.identity.agent_id
        ),
    )
    assert execution_binding_sha256(changed_inputs, ctx) != original
    assert execution_binding_sha256(req, changed_tool) != original
    assert execution_binding_sha256(changed_timeout, ctx) != original
    assert execution_binding_sha256(req, delegated) != original


def test_revocation_is_checked_again_immediately_before_consume(tmp_path):
    class RevokeOnSecondCheck(FakeIndependentAuthority):
        def is_lease_revoked(self, lease_id):
            self.revocation_checks += 1
            return self.revocation_checks >= 2

    req = request()
    authority = RevokeOnSecondCheck()
    with pytest.raises(OmniGateError, match="capability_lease_revoked"):
        OmniProviderAdapter(
            authority, DurableExecutionReplayStore(tmp_path / "revoke-race.sqlite")
        )(req)
    assert authority.revocation_checks == 2
    assert not authority.consumed
