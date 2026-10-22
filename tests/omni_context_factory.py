from __future__ import annotations

import time

from creator_app.agnes.execution.omni import (
    AgentIdentity,
    CapabilityLease,
    EvidenceLevel,
    OMNIExecutionContext,
    PreExecutionRiskVerdict,
    RiskDecision,
)
from creator_app.agnes.execution.request import SkillExecutionRequest


def make_test_omni_context(request: SkillExecutionRequest) -> OMNIExecutionContext:
    """Explicit test-only issuer. Never wire this permissive identity into production."""
    now = time.time()
    capabilities = tuple(request.granted_capabilities) or ("code.read",)
    capability = capabilities[0]
    identity = AgentIdentity(
        "test-agnes-agent",
        "test-model",
        "ck-nexus-test-suite",
        "test-idp:test-agnes-agent",
    )
    policy_id = "test-policy-phase2-phase3"
    return OMNIExecutionContext(
        identity=identity,
        capability_id=capability,
        lease=CapabilityLease(
            "test-lease-" + request.execution_id,
            identity.agent_id,
            capabilities,
            now - 1,
            now + 300,
        ),
        policy_id=policy_id,
        risk_verdict=PreExecutionRiskVerdict(
            "test-risk-" + request.execution_id,
            request.execution_id,
            identity.agent_id,
            capability,
            policy_id,
            RiskDecision.ALLOW,
            EvidenceLevel.E1,
            "LOCAL_TEST_WORKSPACE",
            "reversible",
            "test-data",
            False,
        ),
        tool_id=str(request.plan_step.get("tool_id") or "test-tool"),
        target_id=str(request.plan_step.get("target_id") or "test-target"),
        runtime_id="test-runtime",
        verifier_id="test-verifier",
        evidence_required=True,
        intent_id=request.correlation_id,
    )
