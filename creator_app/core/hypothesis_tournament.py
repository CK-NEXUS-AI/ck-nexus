from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvaluationStance(StrEnum):
    SUPPORT = "support"
    CHALLENGE = "challenge"


class CandidateStatus(StrEnum):
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"


class HypothesisCandidate(BaseModel):
    candidate_id: str
    statement_digest: str
    generation: int = Field(default=0, ge=0)
    parent_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    production_activation_allowed: bool = False


class HypothesisEvaluation(BaseModel):
    evaluator_id: str
    candidate_id: str
    stance: EvaluationStance
    correctness: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    falsifiability: float = Field(ge=0, le=1)
    utility: float = Field(ge=0, le=1)
    independent: bool = True
    safety_veto: bool = False
    evidence_ids: tuple[str, ...] = ()


class TournamentResult(BaseModel):
    candidate_id: str
    status: CandidateStatus
    score: float = Field(default=0, ge=0, le=1)
    evaluator_count: int = Field(default=0, ge=0)
    challenge_count: int = Field(default=0, ge=0)
    evidence_ids: tuple[str, ...] = ()


class HypothesisTournamentPolicy(BaseModel):
    minimum_independent_evaluators: int = Field(default=3, ge=2, le=20)
    require_challenge: bool = True


class HypothesisTournament:
    """Deterministic evaluator quorum with dissent and safety-veto dominance."""

    def __init__(self, policy: HypothesisTournamentPolicy | None = None) -> None:
        self.policy = policy or HypothesisTournamentPolicy()

    def evaluate(
        self,
        candidate: HypothesisCandidate,
        evaluations: list[HypothesisEvaluation],
    ) -> TournamentResult:
        relevant = [
            item
            for item in evaluations
            if item.candidate_id == candidate.candidate_id and item.independent
        ]
        unique_evaluators = {item.evaluator_id for item in relevant}
        evidence_ids = tuple(
            sorted(
                set(candidate.evidence_ids)
                | {
                    evidence_id
                    for item in relevant
                    for evidence_id in item.evidence_ids
                }
            )
        )
        challenge_count = sum(item.stance == EvaluationStance.CHALLENGE for item in relevant)

        blocked = (
            len(unique_evaluators) < self.policy.minimum_independent_evaluators
            or any(item.safety_veto for item in relevant)
            or any(not item.evidence_ids for item in relevant)
            or not candidate.evidence_ids
            or (self.policy.require_challenge and challenge_count == 0)
        )
        if blocked:
            return TournamentResult(
                candidate_id=candidate.candidate_id,
                status=CandidateStatus.BLOCKED,
                evaluator_count=len(unique_evaluators),
                challenge_count=challenge_count,
                evidence_ids=evidence_ids,
            )

        scores = [
            (
                item.correctness * 0.4
                + item.novelty * 0.2
                + item.falsifiability * 0.2
                + item.utility * 0.2
            )
            for item in relevant
        ]
        return TournamentResult(
            candidate_id=candidate.candidate_id,
            status=CandidateStatus.ELIGIBLE,
            score=sum(scores) / len(scores),
            evaluator_count=len(unique_evaluators),
            challenge_count=challenge_count,
            evidence_ids=evidence_ids,
        )

    def rank(
        self,
        candidates: list[HypothesisCandidate],
        evaluations: list[HypothesisEvaluation],
    ) -> list[TournamentResult]:
        results = [self.evaluate(candidate, evaluations) for candidate in candidates]
        return sorted(
            results,
            key=lambda item: (
                item.status != CandidateStatus.ELIGIBLE,
                -item.score,
                item.candidate_id,
            ),
        )

    def propose_offspring(
        self,
        *,
        candidate_id: str,
        statement_digest: str,
        parents: tuple[HypothesisCandidate, ...],
        evidence_ids: tuple[str, ...],
    ) -> HypothesisCandidate:
        if len(parents) < 2:
            raise ValueError("evolution_requires_multiple_parents")
        if not evidence_ids:
            raise ValueError("evolution_requires_evidence")
        if any(not parent.evidence_ids for parent in parents):
            raise ValueError("parent_without_evidence")
        return HypothesisCandidate(
            candidate_id=candidate_id,
            statement_digest=statement_digest,
            generation=max(parent.generation for parent in parents) + 1,
            parent_ids=tuple(parent.candidate_id for parent in parents),
            evidence_ids=evidence_ids,
            production_activation_allowed=False,
        )
