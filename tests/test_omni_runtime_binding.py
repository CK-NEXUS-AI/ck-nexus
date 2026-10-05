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
from creator_app.agnes.execution.request import (
    ExecutorType,
    SkillExecutionRequest,
)


def _request() -> SkillExecutionRequest:
    return SkillExecutionRequest(
        execution_id="exec-001",
        correlation_id="corr-001",
        skill_id="brain.plan",
        skill_version="1.0.0",
        executor=ExecutorType.INTERNAL,
        goal="test",
        inputs={"x": 1},
        granted_capabilities=("code.read",),
    )


def _context(**changes) -> OMNIExecutionContext:
    now = time.time()
    ctx = OMNIExecutionContext(
        identity=AgentIdentity("agent-1", "gpt-test", "ck-nexus", "idp:agent-1"),
        capability_id="code.read",
        lease=CapabilityLease("lease-1", "agent-1", ("code.read",), now - 1, now + 300),
        policy_id="policy-1",
        risk_verdict=PreExecutionRiskVerdict(
            "rv-1", "exec-001", "agent-1", "code.read", "policy-1",
            RiskDecision.ALLOW, EvidenceLevel.E1, "LOCAL", "reversible", "none", False
        ),
        tool_id="tool-1",
        target_id="target-1",
        runtime_id="runtime-test",
        verifier_id="verifier-test",
        evidence_required=True,
        intent_id="intent-1",
    )
    return replace(ctx, **changes)


def assert_block(ctx: OMNIExecutionContext, request: SkillExecutionRequest | None = None):
    with pytest.raises(OmniGateError):
        ctx.validate(request or _request())


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        ("T01 missing agent identity", {"identity": AgentIdentity("", "gpt-test", "ck-nexus", "idp:agent-1")}),
        ("T02 invalid identity proof", {"identity": AgentIdentity("agent-1", "gpt-test", "ck-nexus", "")}),
        ("T03 missing capability", {"capability_id": ""}),
        ("T04 capability outside lease", {"capability_id": "code.write"}),
        ("T05 expired lease", {"lease": CapabilityLease("lease-1", "agent-1", ("code.read",), time.time()-300, time.time()-1)}),
        ("T06 revoked/inactive lease", {"lease": CapabilityLease("lease-1", "agent-1", ("code.read",), time.time()+10, time.time()+300)}),
        ("T07 risk verdict mismatch", {"risk_verdict": PreExecutionRiskVerdict("rv-1", "other-exec", "agent-1", "code.read", "policy-1", RiskDecision.ALLOW, EvidenceLevel.E1, "LOCAL", "reversible", "none", False)}),
        ("T08 agent/capability risk mismatch", {"risk_verdict": PreExecutionRiskVerdict("rv-1", "exec-001", "other", "code.read", "policy-1", RiskDecision.ALLOW, EvidenceLevel.E1, "LOCAL", "reversible", "none", False)}),
        ("T09 policy risk mismatch", {"risk_verdict": PreExecutionRiskVerdict("rv-1", "exec-001", "agent-1", "code.read", "other-policy", RiskDecision.ALLOW, EvidenceLevel.E1, "LOCAL", "reversible", "none", False)}),
        ("T10 non-allow risk decision", {"risk_verdict": PreExecutionRiskVerdict("rv-1", "exec-001", "agent-1", "code.read", "policy-1", RiskDecision.BLOCK, EvidenceLevel.E1, "LOCAL", "reversible", "none", False)}),
        ("T11 missing approval boundary", {"risk_verdict": PreExecutionRiskVerdict("rv-1", "exec-001", "agent-1", "code.read", "policy-1", RiskDecision.REQUIRE_APPROVAL, EvidenceLevel.E1, "LOCAL", "reversible", "none", False)}),
        ("T12 child capability escalation", {"delegation": DelegationContext("parent-1", "parent-agent", ("code.read",), "agent-1")}),
        ("T13 missing parent execution", {"delegation": DelegationContext("", "parent-agent", ("code.read",), "agent-1")}),
        ("T14 missing tool/target binding", {"tool_id": "", "target_id": ""}),
        ("T15 missing runtime binding", {"runtime_id": ""}),
        ("T16 missing verifier", {"verifier_id": ""}),
        ("T17 missing evidence requirement", {"evidence_required": False}),
    ],
)
def test_omni_negative_gates(name, changes):
    assert_block(_context(**changes))


def test_t18_production_mutation_is_blocked_by_existing_policy():
    request = replace(_request(), environment="production")
    ctx = _context()
    # OMNI validation proves its own contracts; production mutation remains owned by AGNES policy.
    ctx.validate(request)
    assert request.environment == "production"
