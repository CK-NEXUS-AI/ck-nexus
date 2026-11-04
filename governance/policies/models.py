from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str
    effect: PolicyEffect
    policy_version: str
    reason: str
    constraints: dict[str, object] = field(default_factory=dict)
