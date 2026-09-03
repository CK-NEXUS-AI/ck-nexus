from __future__ import annotations

from collections.abc import Callable

from .models import ExecutionContext, GuardrailDecision, ToolRequest, WorkflowPattern


class GuardrailEvaluator:
    def __init__(
        self,
        *,
        circuit_open: Callable[[str], bool] | None = None,
        kill_switch_active: Callable[[str], bool] | None = None,
    ) -> None:
        self._circuit_open = circuit_open or (lambda _tool: False)
        self._kill_switch_active = kill_switch_active or (lambda _tenant: False)

    def evaluate(
        self,
        context: ExecutionContext,
        pattern: WorkflowPattern,
        request: ToolRequest,
        *,
        elapsed_seconds: float = 0.0,
    ) -> GuardrailDecision:
        if self._kill_switch_active(context.tenant_id):
            return GuardrailDecision(False, "KILL_SWITCH", "Execution is disabled by control policy.")
        if context.pattern_id != pattern.id or context.pattern_version != pattern.version:
            return GuardrailDecision(False, "PATTERN_VERSION", "Execution pattern version mismatch.")
        if request.tool in pattern.forbidden_tools:
            return GuardrailDecision(False, "FORBIDDEN_TOOL", "Tool is explicitly forbidden by pattern.")
        if request.tool not in pattern.allowed_tools:
            return GuardrailDecision(False, "TOOL_NOT_ALLOWED", "Tool is not allowed by pattern.")
        untrusted_input = context.input_trust != "trusted" or any(
            taint.startswith("untrusted:") for taint in context.input_taints
        )
        sensitive_agent_action = (
            request.side_effecting or request.memory_write or request.cross_agent_handoff
        )
        if untrusted_input and sensitive_agent_action and not context.trusted_confirmation:
            return GuardrailDecision(
                False,
                "UNTRUSTED_INPUT_CONTROL",
                "Untrusted input cannot trigger side effects, memory writes, or agent handoffs without trusted confirmation.",
            )
        if request.required_permission and request.required_permission not in context.permissions:
            return GuardrailDecision(False, "PERMISSION", "Actor lacks required permission.")
        if self._circuit_open(request.tool):
            return GuardrailDecision(False, "CIRCUIT_OPEN", "Tool/provider circuit is open.")
        if request.credential_scope and request.credential_scope.startswith("raw:"):
            return GuardrailDecision(False, "CREDENTIAL_SCOPE", "Raw credential scope is forbidden.")
        if request.requires_approval and context.approval_state != "approved":
            return GuardrailDecision(False, "APPROVAL_REQUIRED", "Human approval is required.")
        if elapsed_seconds >= context.timeout_seconds:
            return GuardrailDecision(False, "TIMEOUT_BUDGET", "Execution timeout budget is exhausted.")
        if context.idempotency_key is None and pattern.side_effect_policy not in {
            "draft_only", "proposal_only", "knowledge_write_only"
        }:
            return GuardrailDecision(False, "IDEMPOTENCY_REQUIRED", "Idempotency key is required.")
        return GuardrailDecision(True, "ALLOW", "Tool request satisfies policy checks.")
