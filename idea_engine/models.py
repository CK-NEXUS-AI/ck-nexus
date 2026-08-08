from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class NodeType(StrEnum):
    IDEA = "idea"
    PROBLEM = "problem"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    DECISION = "decision"
    EXPERIMENT = "experiment"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    CONSTRAINT = "constraint"
    FRAMEWORK_OUTPUT = "framework_output"
    METRIC = "metric"
    PERSONA = "persona"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"


class EdgeType(StrEnum):
    SUPPORTS = "supports"
    CONFLICTS_WITH = "conflicts_with"
    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    DERIVED_FROM = "derived_from"
    ALTERNATIVE_TO = "alternative_to"
    EVIDENCE_FOR = "evidence_for"
    MITIGATES = "mitigates"
    ENABLES = "enables"
    BLOCKS = "blocks"
    VALIDATES = "validates"
    INVALIDATES = "invalidates"


@dataclass(slots=True)
class IdeaNode:
    id: str
    type: str
    title: str
    summary: str
    status: str = "draft"
    tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str | None = None
    raw_input: str = ""
    lens_notes: dict[str, list[str]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class IdeaEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    type: str
    weight: float
    reason: str
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IdeaFeatures:
    idea_type: str
    uncertainty: float = 0.5
    novelty: float = 0.5
    risk: float = 0.5
    evidence_availability: float = 0.5
    time_horizon: str = "medium"


@dataclass(frozen=True, slots=True)
class OpportunityInputs:
    user_value: float
    strategic_fit: float
    reuse_potential: float
    automation_gain: float
    revenue_potential: float
    evidence_strength: float
    reversibility: float
    risk: float
    implementation_cost: float


@dataclass(frozen=True, slots=True)
class ProposalPacket:
    proposal_id: str
    title: str
    summary: str
    recommended_pattern: str
    benefits: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    evidence_needed: tuple[str, ...]
    next_experiments: tuple[str, ...]
    related_node_ids: tuple[str, ...]
    opportunity_score: float
    requires_human_approval: bool = True
