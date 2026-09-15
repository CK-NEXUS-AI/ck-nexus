"""Bridge research sufficiency decisions into Master Controller-compatible intents."""

from __future__ import annotations

from dataclasses import dataclass

from .research_intelligence import (
    ResearchCompilationArtifact,
    ResearchCycleAction,
    decide_research_cycle,
)


@dataclass(frozen=True, slots=True)
class ResearchRoutingPlan:
    action: ResearchCycleAction
    required_lanes: tuple[str, ...]
    controller_command: str
    human_review_required: bool
    reasons: tuple[str, ...]


def build_research_routing_plan(
    query: str,
    artifact: ResearchCompilationArtifact,
    *,
    research_exhausted: bool = False,
) -> ResearchRoutingPlan:
    normalized = query.strip()
    if not normalized:
        raise ValueError("query is required")

    decision = decide_research_cycle(
        artifact,
        research_exhausted=research_exhausted,
    )

    if decision.action is ResearchCycleAction.CONTINUE_RESEARCH:
        return ResearchRoutingPlan(
            action=decision.action,
            required_lanes=("web_research", "agnes", "evidence"),
            controller_command=(
                "research expand verify evidence for: "
                + normalized
            ),
            human_review_required=False,
            reasons=decision.reasons,
        )

    if decision.action is ResearchCycleAction.HUMAN_REVIEW_REQUIRED:
        return ResearchRoutingPlan(
            action=decision.action,
            required_lanes=("agnes", "evidence"),
            controller_command=(
                "review unresolved research contradiction for: "
                + normalized
            ),
            human_review_required=True,
            reasons=decision.reasons,
        )

    return ResearchRoutingPlan(
        action=decision.action,
        required_lanes=("agnes", "evidence"),
        controller_command="analyze evidence-backed research for: " + normalized,
        human_review_required=False,
        reasons=decision.reasons,
    )
