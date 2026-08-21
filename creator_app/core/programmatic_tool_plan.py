from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ToolRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStep(BaseModel):
    step_id: str
    tool_name: str
    intent: str
    risk: ToolRisk = ToolRisk.LOW
    requires_approval: bool = False
    execution_grant_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ProgrammaticToolPlan(BaseModel):
    plan_id: str
    subject: str
    steps: list[ToolStep] = Field(default_factory=list)
    policy_decision_id: str | None = None
    production_promotion_allowed: bool = False

    @property
    def executable(self) -> bool:
        if not self.steps or not self.policy_decision_id:
            return False
        for step in self.steps:
            if not step.intent.strip():
                return False
            if (
                step.risk in {ToolRisk.HIGH, ToolRisk.CRITICAL}
                and (not step.requires_approval or not step.execution_grant_id)
            ):
                return False
            if step.requires_approval and not step.execution_grant_id:
                return False
        return True


class ToolPlanPolicy:
    """Fail-closed policy for model-generated lightweight tool orchestration."""

    @staticmethod
    def validate(plan: ProgrammaticToolPlan) -> None:
        if not plan.executable:
            raise ValueError("tool plan is not executable under current policy")
