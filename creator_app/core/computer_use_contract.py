from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from creator_app.core.policy_errors import PolicyViolation


class ComputerEnvironment(StrEnum):
    BROWSER = "browser"
    DESKTOP = "desktop"
    MOBILE = "mobile"


class ComputerActionRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComputerActionProposal(BaseModel):
    action_id: str
    environment: ComputerEnvironment
    action_type: str
    target: str | None = None
    intent: str = ""
    screenshot_digest: str
    prompt_injection_scan_evidence_ids: list[str] = Field(default_factory=list)
    risk: ComputerActionRisk = ComputerActionRisk.HIGH
    approval_required: bool = True
    execution_grant_id: str | None = None


class ComputerUsePolicy:
    """Model proposes actions; CK-NEXUS decides whether execution is permitted."""

    @staticmethod
    def execution_allowed(proposal: ComputerActionProposal) -> bool:
        if not proposal.screenshot_digest:
            return False
        if not proposal.prompt_injection_scan_evidence_ids:
            return False
        if proposal.risk in {ComputerActionRisk.HIGH, ComputerActionRisk.CRITICAL}:
            return bool(proposal.execution_grant_id)
        if proposal.approval_required and not proposal.execution_grant_id:
            return False
        return True

    @classmethod
    def require_execution_allowed(cls, proposal: ComputerActionProposal) -> None:
        if not cls.execution_allowed(proposal):
            raise PolicyViolation("computer action blocked by CK-NEXUS policy")
