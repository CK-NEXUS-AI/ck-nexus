from __future__ import annotations

from pydantic import BaseModel

from creator_app.core.autonomous_builder import AutonomousCapabilityBuilder, BuildPlan
from creator_app.core.dual_track_council import CouncilDecision, DualTrackCouncil


class IntelligenceCycleResult(BaseModel):
    proposal_id: str
    council: CouncilDecision
    build_plan: BuildPlan


class AgnesIntelligencePipeline:
    """Coordinates council decision and governed Post-P0 build progression."""

    def __init__(
        self,
        *,
        council: DualTrackCouncil,
        builder: AutonomousCapabilityBuilder,
    ) -> None:
        self._council = council
        self._builder = builder

    def evaluate(
        self,
        *,
        proposal_id: str,
        track: str,
        capability_id: str,
        base_commit: str,
        base_tree: str,
        evidence_ids: list[str] | None = None,
    ) -> IntelligenceCycleResult:
        council = self._council.decide(
            proposal_id=proposal_id,
            track=track,
            evidence_ids=evidence_ids,
        )
        plan = BuildPlan(
            proposal_id=proposal_id,
            capability_id=capability_id,
            base_commit=base_commit,
            base_tree=base_tree,
            evidence_ids=list(evidence_ids or []),
        )
        if council.decision.value not in {
            "LOCAL_EVALUATE",
            "IMPLEMENT_POST_P0",
        }:
            plan.blockers.append(f"council decision: {council.decision.value}")
        plan = self._builder.advance(plan)
        return IntelligenceCycleResult(
            proposal_id=proposal_id,
            council=council,
            build_plan=plan,
        )
