from __future__ import annotations

import asyncio
import uuid

import pytest

from orchestration.controller import ExecutionController
from orchestration.guardrails import GuardrailEvaluator
from orchestration.models import (
    ExecutionContext,
    ExecutionRecord,
    ExecutionState,
    ToolRequest,
)
from orchestration.registry import PatternRegistry
from orchestration.selector import PatternSelector


class FakeExecutor:
    async def execute(self, request):
        return {"tool": request.tool, "ok": True}


def context(pattern, *, approval="pending", permissions=(), idempotency="idem-1"):
    return ExecutionContext(
        execution_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        actor_id="user-1",
        roles=frozenset({"owner"}),
        permissions=frozenset(permissions),
        correlation_id=str(uuid.uuid4()),
        environment="staging",
        policy_version="2026-08-09.1",
        pattern_id=pattern.id,
        pattern_version=pattern.version,
        max_steps=pattern.max_steps,
        timeout_seconds=pattern.timeout_seconds,
        approval_state=approval,
        idempotency_key=idempotency,
    )


def test_registry_loads_six_versioned_patterns():
    registry = PatternRegistry.from_file()
    assert len(registry.all()) == 6
    assert registry.get("dataops_release_gate", "1.0").version == "1.0"


def test_selector_prefers_high_risk_release_pattern_deterministically():
    selector = PatternSelector(PatternRegistry.from_file())
    result = selector.select("run staging release security test")
    assert result.pattern_id == "dataops_release_gate"
    assert result.requires_human_approval is True
    assert result.confidence >= 0.7


def test_unknown_intent_routes_to_human_review():
    result = PatternSelector(PatternRegistry.from_file()).select("totally novel unmapped request")
    assert result.pattern_id is None
    assert result.requires_human_approval is True


def test_state_machine_rejects_invalid_transition():
    pattern = PatternRegistry.from_file().get("product_idea_exploration")
    record = ExecutionRecord(context(pattern))
    with pytest.raises(ValueError):
        record.transition(ExecutionState.COMPLETED)


def test_forbidden_tool_is_denied_even_if_actor_is_owner():
    pattern = PatternRegistry.from_file().get("product_idea_exploration")
    decision = GuardrailEvaluator().evaluate(
        context(pattern, approval="approved", permissions=("deploy",)),
        pattern,
        ToolRequest("s1", "engineering", "deploy", required_permission="deploy"),
    )
    assert decision.allowed is False
    assert decision.code == "FORBIDDEN_TOOL"


def test_approval_bypass_is_denied():
    pattern = PatternRegistry.from_file().get("credential_anomaly_monitor")
    decision = GuardrailEvaluator().evaluate(
        context(pattern, approval="pending", idempotency="idem"),
        pattern,
        ToolRequest("s1", "security_reviewer", "alert_write", requires_approval=True),
    )
    assert decision.code == "APPROVAL_REQUIRED"


def test_execution_controller_owns_side_effect_seam_and_audits_pattern_version():
    pattern = PatternRegistry.from_file().get("dataops_release_gate")
    record = ExecutionRecord(context(pattern, approval="approved", idempotency="idem"))
    controller = ExecutionController(GuardrailEvaluator(), FakeExecutor())
    request = ToolRequest("s1", "engineering", "test")
    output = asyncio.run(controller.execute_step(record, pattern, request))
    assert output["ok"] is True
    assert record.step_count == 1
    assert record.audit[-1]["pattern_version"] == "1.0"


def test_kill_switch_blocks_execution():
    pattern = PatternRegistry.from_file().get("dataops_release_gate")
    evaluator = GuardrailEvaluator(kill_switch_active=lambda tenant: tenant == "tenant-1")
    decision = evaluator.evaluate(context(pattern), pattern, ToolRequest("s1", "engineering", "test"))
    assert decision.code == "KILL_SWITCH"
