from creator_app.agnes.standards import (
    ProtocolRegistry,
    CompatibilityResult,
    ToolGuardrailCoverage,
    ToolKind,
    StandardsBaseline,
    StandardStatus,
    build_genai_span_attributes,
)


def test_mcp_latest_is_current():
    assert ProtocolRegistry.compatibility("mcp", "2026-07-28") is CompatibilityResult.CURRENT


def test_mcp_legacy_requires_migration():
    assert ProtocolRegistry.compatibility("mcp", "2025-11-25") is CompatibilityResult.MIGRATION_REQUIRED


def test_a2a_latest_is_current():
    assert ProtocolRegistry.compatibility("a2a", "1.0.0") is CompatibilityResult.CURRENT


def test_non_function_tools_require_ck_guard():
    for kind in (
        ToolKind.HOSTED,
        ToolKind.COMPUTER,
        ToolKind.SHELL,
        ToolKind.APPLY_PATCH,
        ToolKind.AGENT_AS_TOOL,
        ToolKind.HANDOFF,
        ToolKind.MCP_REMOTE,
    ):
        decision = ToolGuardrailCoverage.decision(kind)
        assert decision.requires_ck_pre_execution_guard is True
        assert decision.covered_by_native_tool_guardrail is False


def test_function_tool_still_requires_ck_governor():
    decision = ToolGuardrailCoverage.decision(ToolKind.FUNCTION)
    assert decision.covered_by_native_tool_guardrail is True
    assert decision.requires_ck_pre_execution_guard is True


def test_cyber_ai_profile_is_not_marked_final():
    record = StandardsBaseline.get("nist_cyber_ai_profile")
    assert record.status is StandardStatus.DEVELOPMENT


def test_genai_attributes_do_not_require_raw_content():
    attrs = build_genai_span_attributes(
        operation_name="chat",
        provider_name="example",
        model_name="model",
        ck_run_id="run-1",
        ck_evidence_id="evd-1",
        input_tokens=10,
        output_tokens=4,
        tool_type="function",
    )
    assert attrs["ck.run.id"] == "run-1"
    assert attrs["ck.evidence.id"] == "evd-1"
    assert all("prompt" not in key for key in attrs)
