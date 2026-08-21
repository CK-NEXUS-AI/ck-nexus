from __future__ import annotations

from pydantic import BaseModel, Field

from .debate_engine import Decision, StructuredDebateEngine


class CouncilDecision(BaseModel):
    proposal_id: str
    decision: Decision
    track: str
    reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class DualTrackCouncil:
    """Coordinates governed-core and experimental-lab proposal decisions."""

    def __init__(self, debate_engine: StructuredDebateEngine) -> None:
        self._debate_engine = debate_engine

    def decide(
        self,
        *,
        proposal_id: str,
        track: str,
        evidence_ids: list[str] | None = None,
    ) -> CouncilDecision:
        if track not in {"governed_core", "experimental_lab"}:
            raise ValueError("unknown council track")

        result = self._debate_engine.resolve(proposal_id)
        decision = Decision(str(result["decision"]))
        reasons: list[str] = []

        if decision == Decision.PENDING:
            missing = result.get("missing_roles", [])
            reasons.append(f"missing required roles: {missing}")
        elif decision == Decision.REJECT:
            reasons.append("verifier/red-team veto or negative council outcome")
        elif track == "experimental_lab" and decision == Decision.IMPLEMENT_POST_P0:
            reasons.append("eligible only for isolated Post-P0 implementation")
        else:
            reasons.append("structured debate requirements satisfied")

        return CouncilDecision(
            proposal_id=proposal_id,
            decision=decision,
            track=track,
            reasons=reasons,
            evidence_ids=list(evidence_ids or []),
        )
