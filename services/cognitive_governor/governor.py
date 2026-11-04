from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.cognitive_fabric.models import CognitiveRequest


class RiskClass(str, Enum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class GovernorDecision:
    allowed: bool
    requires_approval: bool
    risk: RiskClass
    reason: str


class CognitiveGovernor:
    """Fail-closed policy boundary between model proposals and execution."""

    async def evaluate(self, request: CognitiveRequest) -> GovernorDecision:
        risk_value = request.metadata.get("risk", RiskClass.READ_ONLY.value)
        try:
            risk = RiskClass(str(risk_value))
        except ValueError:
            return GovernorDecision(False, True, RiskClass.CRITICAL, "unknown risk classification")

        if risk is RiskClass.CRITICAL:
            return GovernorDecision(False, True, risk, "critical actions are denied by default")
        if risk is RiskClass.HIGH:
            return GovernorDecision(True, True, risk, "high-impact action requires approval")
        return GovernorDecision(True, False, risk, "policy allowed")
