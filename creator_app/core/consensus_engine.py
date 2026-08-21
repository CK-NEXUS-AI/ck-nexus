from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class VoteType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    ABSTAIN = "abstain"


class ConsensusRule(StrEnum):
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    SUPER_MAJORITY = "super_majority"
    WEIGHTED = "weighted"


class ConsensusStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISE_REQUESTED = "revise_requested"
    ESCALATED = "escalated"


class AgentVote(BaseModel):
    voter_id: str
    role: str
    vote: VoteType
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    weight: float | None = Field(default=None, gt=0)


class ConsensusDecision(BaseModel):
    status: ConsensusStatus
    rule: ConsensusRule
    approval_score: float
    rejection_score: float
    participating_voters: int
    escalation_reason: str | None = None


class ConsensusEngine:
    """Evaluates evidence-backed votes without allowing silent self-approval."""

    DEFAULT_ROLE_WEIGHTS: dict[str, float] = {
        "verifier": 3.0,
        "reviewer": 2.0,
        "challenger": 2.0,
        "architect": 1.5,
        "builder": 1.0,
        "researcher": 1.0,
        "scout": 0.5,
    }

    def evaluate(
        self,
        votes: list[AgentVote],
        *,
        rule: ConsensusRule,
    ) -> ConsensusDecision:
        if not votes:
            return self._escalated(rule, "no votes supplied")

        active_votes = [vote for vote in votes if vote.vote != VoteType.ABSTAIN]
        if not active_votes:
            return self._escalated(rule, "all voters abstained")

        if rule == ConsensusRule.WEIGHTED:
            return self._evaluate_weighted(active_votes)

        approvals = sum(vote.vote == VoteType.APPROVE for vote in active_votes)
        rejections = sum(vote.vote == VoteType.REJECT for vote in active_votes)
        revisions = sum(vote.vote == VoteType.REVISE for vote in active_votes)
        total = len(active_votes)

        if rule == ConsensusRule.UNANIMOUS:
            if approvals == total:
                return self._decision(
                    ConsensusStatus.ACCEPTED,
                    rule,
                    approvals,
                    rejections,
                    total,
                )
            if rejections > 0:
                return self._decision(
                    ConsensusStatus.REJECTED,
                    rule,
                    approvals,
                    rejections,
                    total,
                )
            if revisions > 0:
                return self._decision(
                    ConsensusStatus.REVISE_REQUESTED,
                    rule,
                    approvals,
                    rejections,
                    total,
                )
            return self._escalated(rule, "unanimous consensus not reached", total)

        threshold = total / 2
        if rule == ConsensusRule.SUPER_MAJORITY:
            threshold = (2 * total) / 3

        if approvals > threshold or (
            rule == ConsensusRule.SUPER_MAJORITY and approvals >= threshold
        ):
            return self._decision(
                ConsensusStatus.ACCEPTED,
                rule,
                approvals,
                rejections,
                total,
            )
        if rejections > threshold or (
            rule == ConsensusRule.SUPER_MAJORITY and rejections >= threshold
        ):
            return self._decision(
                ConsensusStatus.REJECTED,
                rule,
                approvals,
                rejections,
                total,
            )
        if revisions > 0:
            return self._decision(
                ConsensusStatus.REVISE_REQUESTED,
                rule,
                approvals,
                rejections,
                total,
            )
        return self._escalated(rule, "consensus threshold not reached", total)

    def _evaluate_weighted(self, votes: list[AgentVote]) -> ConsensusDecision:
        approval_weight = 0.0
        rejection_weight = 0.0
        revise_weight = 0.0
        total_weight = 0.0

        for vote in votes:
            weight = vote.weight or self.DEFAULT_ROLE_WEIGHTS.get(vote.role, 1.0)
            total_weight += weight
            if vote.vote == VoteType.APPROVE:
                approval_weight += weight
            elif vote.vote == VoteType.REJECT:
                rejection_weight += weight
            elif vote.vote == VoteType.REVISE:
                revise_weight += weight

        if approval_weight > total_weight / 2:
            status = ConsensusStatus.ACCEPTED
        elif rejection_weight > total_weight / 2:
            status = ConsensusStatus.REJECTED
        elif revise_weight > 0:
            status = ConsensusStatus.REVISE_REQUESTED
        else:
            return self._escalated(
                ConsensusRule.WEIGHTED,
                "weighted consensus threshold not reached",
                len(votes),
            )

        return ConsensusDecision(
            status=status,
            rule=ConsensusRule.WEIGHTED,
            approval_score=approval_weight,
            rejection_score=rejection_weight,
            participating_voters=len(votes),
        )

    @staticmethod
    def _decision(
        status: ConsensusStatus,
        rule: ConsensusRule,
        approvals: float,
        rejections: float,
        total: int,
    ) -> ConsensusDecision:
        return ConsensusDecision(
            status=status,
            rule=rule,
            approval_score=float(approvals),
            rejection_score=float(rejections),
            participating_voters=total,
        )

    @staticmethod
    def _escalated(
        rule: ConsensusRule,
        reason: str,
        total: int = 0,
    ) -> ConsensusDecision:
        return ConsensusDecision(
            status=ConsensusStatus.ESCALATED,
            rule=rule,
            approval_score=0.0,
            rejection_score=0.0,
            participating_voters=total,
            escalation_reason=reason,
        )
