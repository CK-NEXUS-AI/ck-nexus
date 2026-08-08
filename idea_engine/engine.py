from __future__ import annotations

import uuid
from pathlib import Path

from .graph import IdeaGraph
from .lenses import select_lenses
from .models import IdeaFeatures, IdeaNode, NodeType, OpportunityInputs, ProposalPacket
from .scoring import opportunity_score

STAGES = (
    "clarify_blind_spots",
    "improve_understanding",
    "decision_strategy",
    "creative_problem_solving",
    "self_reflection",
    "data_insight",
    "hidden_opportunity",
    "structure",
)


class IdeaEngine:
    """Proposal-only R11 engine. It has no mutation/deploy/send/billing credential tools."""

    FORBIDDEN_CAPABILITIES = frozenset({
        "deploy", "external_send", "publish", "billing_mutation", "credential_export",
        "approval_mutation", "release_gate_mutation",
    })

    def __init__(self, graph: IdeaGraph | None = None) -> None:
        self.graph = graph or IdeaGraph(Path("idea_graph.json"))

    def expand(
        self,
        *,
        title: str,
        raw_input: str,
        features: IdeaFeatures,
        tags: list[str] | None = None,
        source_refs: list[str] | None = None,
        confidence: float = 0.5,
    ) -> tuple[IdeaNode, tuple[object, ...], tuple[str, ...]]:
        selected_lenses = select_lenses(features)
        node = IdeaNode(
            id=str(uuid.uuid4()),
            type=NodeType.IDEA.value,
            title=title.strip(),
            summary=raw_input.strip(),
            raw_input=raw_input.strip(),
            tags=list(tags or []),
            source_refs=list(source_refs or []),
            confidence=max(0.0, min(1.0, confidence)),
            lens_notes={stage: [] for stage in STAGES},
        )
        self.graph.add_node(node)
        links = self.graph.link_similar(node)
        return node, links, selected_lenses

    def make_proposal(
        self,
        *,
        node: IdeaNode,
        score_inputs: OpportunityInputs,
        benefits: list[str] | None = None,
        risks: list[str] | None = None,
        assumptions: list[str] | None = None,
        evidence_needed: list[str] | None = None,
        next_experiments: list[str] | None = None,
    ) -> ProposalPacket:
        related = tuple(
            edge.to_node_id
            for edge in self.graph.edges.values()
            if edge.from_node_id == node.id
        )
        return ProposalPacket(
            proposal_id=str(uuid.uuid4()),
            title=node.title,
            summary=node.summary,
            recommended_pattern="product_idea_exploration",
            benefits=tuple(benefits or ()),
            risks=tuple(risks or ()),
            assumptions=tuple(assumptions or ()),
            evidence_needed=tuple(evidence_needed or ()),
            next_experiments=tuple(next_experiments or ()),
            related_node_ids=related,
            opportunity_score=opportunity_score(score_inputs),
            requires_human_approval=True,
        )

    def assert_capability_allowed(self, capability: str) -> None:
        if capability in self.FORBIDDEN_CAPABILITIES:
            raise PermissionError("Idea Engine is proposal-only and cannot perform this capability.")
