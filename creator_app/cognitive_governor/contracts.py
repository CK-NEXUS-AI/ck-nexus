"""Deterministic decision contracts for the CK-NEXUS Cognitive Governor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionClass(StrEnum):
    READ = "read"
    ANALYZE = "analyze"
    DRAFT = "draft"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    PRODUCTION_MUTATION = "production_mutation"


class ExecutionMode(StrEnum):
    SINGLE = "single"
    FALLBACK = "fallback"
    PARALLEL = "parallel"
    COUNCIL = "council"
    DEBATE = "debate"
    SHADOW = "shadow"


@dataclass(frozen=True, slots=True)
class CognitiveRequest:
    goal: str
    action_class: ActionClass
    required_capabilities: frozenset[str]
    complexity: int = 1
    budget_tier: int = 1
    user_approved: bool = False
    production_authorized: bool = False
    safety_veto: bool = False
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal must not be empty")
        if not 1 <= self.complexity <= 5:
            raise ValueError("complexity must be between 1 and 5")
        if not 0 <= self.budget_tier <= 5:
            raise ValueError("budget_tier must be between 0 and 5")


@dataclass(frozen=True, slots=True)
class PlanNode:
    node_id: str
    role: str
    capability: str
    dependencies: tuple[str, ...] = ()
    independently_verified: bool = False


@dataclass(frozen=True, slots=True)
class CognitiveDecision:
    allowed: bool
    risk: RiskLevel
    mode: ExecutionMode
    approval_required: bool
    reason: str
    team: tuple[str, ...]
    nodes: tuple[PlanNode, ...]
    authority: str = "CK-NEXUS"
