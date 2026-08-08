from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from creator_app.agnes_skills import SkillDefinition, SkillRisk

from .request import ExecutorRiskClass, SkillExecutionRequest


class ExecutionBlocked(PermissionError):
    pass


class RiskClassifier:
    _skill_risk = {
        SkillRisk.READ_ONLY: ExecutorRiskClass.READ_ONLY,
        SkillRisk.LOCAL_WRITE: ExecutorRiskClass.MEDIUM,
        SkillRisk.EXTERNAL_WRITE: ExecutorRiskClass.HIGH,
        SkillRisk.HIGH_IMPACT: ExecutorRiskClass.CRITICAL,
    }
    _capability_floor = {
        "code_write": ExecutorRiskClass.HIGH,
        "patch": ExecutorRiskClass.HIGH,
        "workspace": ExecutorRiskClass.HIGH,
        "terminal": ExecutorRiskClass.HIGH,
        "self_upgrade": ExecutorRiskClass.CRITICAL,
        "orchestration": ExecutorRiskClass.HIGH,
        "knowledge_write": ExecutorRiskClass.MEDIUM,
    }

    def classify(self, skill: SkillDefinition, executor_risk: ExecutorRiskClass | None = None) -> ExecutorRiskClass:
        candidates = [self._skill_risk[skill.risk]]
        candidates.extend(
            risk for capability, risk in self._capability_floor.items() if capability in skill.capabilities
        )
        if executor_risk is not None:
            candidates.append(executor_risk)
        return max(candidates, key=lambda item: item.rank)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool


class AgnesPolicyLike(Protocol):
    allow_production_mutation: bool


class ExecutionPolicyEngine:
    def __init__(self, policy: AgnesPolicyLike) -> None:
        self.policy = policy

    def evaluate(
        self,
        request: SkillExecutionRequest,
        *,
        skill: SkillDefinition,
        risk_class: ExecutorRiskClass,
    ) -> PolicyDecision:
        if request.environment == "production" and risk_class.rank > ExecutorRiskClass.READ_ONLY.rank:
            if not self.policy.allow_production_mutation:
                return PolicyDecision(False, "production_mutation_disabled", True)
        requires_approval = (
            request.requires_approval
            or skill.approval_required
            or risk_class.rank >= ExecutorRiskClass.HIGH.rank
        )
        return PolicyDecision(True, "allowed", requires_approval)
