from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolKind(str, Enum):
    FUNCTION = "FUNCTION"
    HOSTED = "HOSTED"
    COMPUTER = "COMPUTER"
    SHELL = "SHELL"
    APPLY_PATCH = "APPLY_PATCH"
    AGENT_AS_TOOL = "AGENT_AS_TOOL"
    HANDOFF = "HANDOFF"
    MCP_REMOTE = "MCP_REMOTE"


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    covered_by_native_tool_guardrail: bool
    requires_ck_pre_execution_guard: bool
    reason: str


class ToolGuardrailCoverage:
    """Fail-closed coverage matrix for tool execution boundaries.

    Native SDK guardrail support is not assumed across all tool classes. CK-NEXUS
    must preserve its own pre-execution policy boundary whenever coverage is absent
    or runtime-specific.
    """

    _NATIVE_FUNCTION_GUARDRAIL = {ToolKind.FUNCTION}

    @classmethod
    def decision(cls, kind: ToolKind) -> GuardrailDecision:
        native = kind in cls._NATIVE_FUNCTION_GUARDRAIL
        if native:
            return GuardrailDecision(
                covered_by_native_tool_guardrail=True,
                requires_ck_pre_execution_guard=True,
                reason=(
                    "native function-tool guardrails may exist, but CK Governor still "
                    "remains the independent execution authority"
                ),
            )
        return GuardrailDecision(
            covered_by_native_tool_guardrail=False,
            requires_ck_pre_execution_guard=True,
            reason=(
                "no universal native tool-guardrail guarantee for this tool class; "
                "CK must enforce policy/approval before execution"
            ),
        )
