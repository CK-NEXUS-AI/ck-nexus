from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class ExpertProfile:
    expert_id: str
    agent_id: str
    domains: tuple[str, ...]
    capabilities: tuple[str, ...] = ()
    may_verify: bool = False


@dataclass(frozen=True)
class ExpertRoute:
    domains: tuple[str, ...]
    primary_expert: str
    supporting_experts: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    risk_class: RiskClass
    approval_required: bool
    independent_verifier_required: bool
    needs_discovery: bool
    rationale: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "domains": list(self.domains),
            "primary_expert": self.primary_expert,
            "supporting_experts": list(self.supporting_experts),
            "required_capabilities": list(self.required_capabilities),
            "risk_class": self.risk_class.value,
            "approval_required": self.approval_required,
            "independent_verifier_required": self.independent_verifier_required,
            "needs_discovery": self.needs_discovery,
            "rationale": list(self.rationale),
        }
