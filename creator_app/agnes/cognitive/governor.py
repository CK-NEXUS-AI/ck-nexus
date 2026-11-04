"""Fail-closed cognitive governor contracts.

The governor decides whether a proposed action may proceed. It does not execute actions,
release credentials, or declare production readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class GovernorDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class ActionProposal:
    action: str
    actor: str
    scope: str
    risk: RiskLevel = RiskLevel.UNKNOWN
    external_write: bool = False
    destructive: bool = False
    production_mutation: bool = False
    verified: bool = False
    human_approved: bool = False
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    decision: GovernorDecision
    reasons: tuple[str, ...]
    requires_verification: bool
    requires_human_approval: bool


class CognitiveGovernor:
    """Deterministic authority boundary for proposed cognitive actions."""

    def decide(self, proposal: ActionProposal) -> GovernanceResult:
        reasons: list[str] = []

        if proposal.risk is RiskLevel.UNKNOWN:
            return GovernanceResult(
                decision=GovernorDecision.DENY,
                reasons=("unknown risk is fail-closed",),
                requires_verification=True,
                requires_human_approval=True,
            )

        if proposal.production_mutation:
            reasons.append("production mutation requires separate release authority")
            return GovernanceResult(
                decision=GovernorDecision.DENY,
                reasons=tuple(reasons),
                requires_verification=True,
                requires_human_approval=True,
            )

        sensitive = proposal.external_write or proposal.destructive
        elevated = proposal.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}

        if sensitive or elevated:
            if not proposal.verified:
                reasons.append("independent verification required")
            if not proposal.human_approved:
                reasons.append("human approval required")
            if not proposal.evidence_refs:
                reasons.append("evidence reference required")
            if reasons:
                return GovernanceResult(
                    decision=GovernorDecision.REQUIRE_APPROVAL,
                    reasons=tuple(reasons),
                    requires_verification=True,
                    requires_human_approval=True,
                )

        return GovernanceResult(
            decision=GovernorDecision.ALLOW,
            reasons=("proposal satisfies bounded governance contract",),
            requires_verification=sensitive or elevated,
            requires_human_approval=sensitive or elevated,
        )
