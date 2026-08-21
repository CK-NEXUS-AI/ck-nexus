from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class RoleType(StrEnum):
    ARCHITECT = "architect"
    BUILDER = "builder"
    UPDATER = "updater"
    VERIFIER = "verifier"
    RED_TEAM = "red_team"
    RESEARCHER = "researcher"
    SCOUT = "scout"
    PROTOTYPE_BUILDER = "prototype_builder"
    EVALUATOR = "evaluator"
    CHALLENGER = "challenger"
    GOVERNOR = "governor"


class Decision(StrEnum):
    PENDING = "PENDING"
    REJECT = "REJECT"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    LOCAL_EVALUATE = "LOCAL_EVALUATE"
    IMPLEMENT_POST_P0 = "IMPLEMENT_POST_P0"
    ELIGIBLE_FOR_PROMOTION_REVIEW = "ELIGIBLE_FOR_PROMOTION_REVIEW"


class Argument(BaseModel):
    role: RoleType
    content: str
    evidence_ids: list[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
    veto: bool = False


class Proposal(BaseModel):
    proposal_id: str
    title: str
    description: str
    base_commit: str
    base_tree: str
    arguments: list[Argument] = Field(default_factory=list)
    decision: Decision = Decision.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StructuredDebateEngine:
    """Role-separated debate with explicit verifier/red-team vetoes."""

    REQUIRED_ROLES = {RoleType.ARCHITECT, RoleType.VERIFIER, RoleType.RED_TEAM}

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}

    def create_proposal(
        self,
        *,
        title: str,
        description: str,
        base_commit: str,
        base_tree: str,
    ) -> str:
        proposal_id = str(uuid4())
        self._proposals[proposal_id] = Proposal(
            proposal_id=proposal_id,
            title=title,
            description=description,
            base_commit=base_commit,
            base_tree=base_tree,
        )
        return proposal_id

    def add_argument(self, proposal_id: str, argument: Argument) -> None:
        self._proposals[proposal_id].arguments.append(argument)

    def get(self, proposal_id: str) -> Proposal:
        return self._proposals[proposal_id]

    def resolve(self, proposal_id: str) -> dict[str, object]:
        proposal = self.get(proposal_id)
        roles = {argument.role for argument in proposal.arguments}
        missing = sorted(role.value for role in self.REQUIRED_ROLES - roles)
        if missing:
            return {"decision": Decision.PENDING.value, "missing_roles": missing}

        vetoes = [
            argument
            for argument in proposal.arguments
            if argument.veto
            and argument.role in {RoleType.VERIFIER, RoleType.RED_TEAM}
        ]
        if vetoes:
            proposal.decision = Decision.REJECT
            return {
                "decision": proposal.decision.value,
                "veto_roles": [argument.role.value for argument in vetoes],
            }

        total_score = sum(argument.score for argument in proposal.arguments)
        if total_score >= 1.5:
            proposal.decision = Decision.IMPLEMENT_POST_P0
        elif total_score >= 0.5:
            proposal.decision = Decision.LOCAL_EVALUATE
        elif total_score <= -0.5:
            proposal.decision = Decision.REJECT
        else:
            proposal.decision = Decision.RESEARCH_ONLY

        return {
            "decision": proposal.decision.value,
            "total_score": total_score,
            "roles": sorted(role.value for role in roles),
        }
