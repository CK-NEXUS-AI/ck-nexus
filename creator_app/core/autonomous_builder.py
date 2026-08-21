from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BuilderStage(StrEnum):
    DISCOVER = "discover"
    RESEARCH = "research"
    DESIGN = "design"
    BUILD = "build"
    TEST = "test"
    VERIFY = "verify"
    REGISTER = "register"
    MONITOR = "monitor"
    BLOCKED = "blocked"


class BuildPlan(BaseModel):
    proposal_id: str
    capability_id: str
    base_commit: str
    base_tree: str
    stage: BuilderStage = BuilderStage.DISCOVER
    evidence_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    production_promotion_allowed: bool = False


class AutonomousCapabilityBuilder:
    """State machine for autonomous Post-P0 capability development.

    It does not execute external writes by itself. Execution is delegated to governed adapters.
    """

    _ORDER = [
        BuilderStage.DISCOVER,
        BuilderStage.RESEARCH,
        BuilderStage.DESIGN,
        BuilderStage.BUILD,
        BuilderStage.TEST,
        BuilderStage.VERIFY,
        BuilderStage.REGISTER,
        BuilderStage.MONITOR,
    ]

    def advance(self, plan: BuildPlan, *, evidence_id: str | None = None) -> BuildPlan:
        if plan.blockers:
            plan.stage = BuilderStage.BLOCKED
            return plan
        if evidence_id:
            plan.evidence_ids.append(evidence_id)
        if plan.stage == BuilderStage.BLOCKED:
            return plan
        try:
            index = self._ORDER.index(plan.stage)
        except ValueError:
            return plan
        if index < len(self._ORDER) - 1:
            plan.stage = self._ORDER[index + 1]
        return plan
