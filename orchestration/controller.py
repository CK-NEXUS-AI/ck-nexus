from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .guardrails import GuardrailEvaluator
from .models import ExecutionRecord, ToolRequest, WorkflowPattern


class ToolExecutor(Protocol):
    async def execute(self, request: ToolRequest) -> object: ...


@dataclass(slots=True)
class ExecutionController:
    evaluator: GuardrailEvaluator
    executor: ToolExecutor

    async def execute_step(
        self,
        record: ExecutionRecord,
        pattern: WorkflowPattern,
        request: ToolRequest,
        *,
        elapsed_seconds: float = 0.0,
    ) -> object:
        if record.step_count >= record.context.max_steps:
            raise RuntimeError("max step budget exhausted")
        decision = self.evaluator.evaluate(
            record.context, pattern, request, elapsed_seconds=elapsed_seconds
        )
        record.audit.append(
            {
                "event": "guardrail_decision",
                "execution_id": record.context.execution_id,
                "pattern_id": pattern.id,
                "pattern_version": pattern.version,
                "step_id": request.step_id,
                "tool": request.tool,
                "decision": decision.code,
                "allowed": decision.allowed,
            }
        )
        if not decision.allowed:
            raise PermissionError(decision.code)
        output = await self.executor.execute(request)
        record.step_count += 1
        return output
