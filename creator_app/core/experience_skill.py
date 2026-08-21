from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PromotionDecision(StrEnum):
    PROMOTE = "promote"
    HOLD = "hold"
    REJECT = "reject"


class ExperienceRecord(BaseModel):
    experience_id: str = Field(min_length=1)
    skill_key: str = Field(min_length=1)
    success: bool
    quality_score: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)


class SkillPromotionPolicy(BaseModel):
    minimum_samples: int = Field(default=3, ge=1)
    minimum_success_rate: float = Field(default=0.8, ge=0, le=1)
    minimum_quality_score: float = Field(default=0.75, ge=0, le=1)
    minimum_distinct_evidence: int = Field(default=2, ge=1)


class SkillCandidate(BaseModel):
    skill_key: str
    decision: PromotionDecision
    sample_count: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=1)
    average_quality: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str


class ExperienceSkillEngine:
    """Promotes repeated verified experience into a skill candidate, never directly into runtime."""

    def __init__(self, policy: SkillPromotionPolicy | None = None) -> None:
        self.policy = policy or SkillPromotionPolicy()

    def evaluate(self, records: list[ExperienceRecord], *, skill_key: str) -> SkillCandidate:
        relevant = [record for record in records if record.skill_key == skill_key]
        if not relevant:
            return SkillCandidate(
                skill_key=skill_key,
                decision=PromotionDecision.REJECT,
                sample_count=0,
                success_rate=0.0,
                average_quality=0.0,
                reason="no matching experience records",
            )

        sample_count = len(relevant)
        successes = sum(record.success for record in relevant)
        success_rate = successes / sample_count
        average_quality = sum(record.quality_score for record in relevant) / sample_count
        evidence_ids = sorted(
            {evidence for record in relevant for evidence in record.evidence_ids}
        )

        if any(record.success and not record.evidence_ids for record in relevant):
            decision = PromotionDecision.REJECT
            reason = "successful experience without evidence"
        elif len(evidence_ids) < self.policy.minimum_distinct_evidence:
            decision = PromotionDecision.HOLD
            reason = "insufficient independent evidence"
        elif sample_count < self.policy.minimum_samples:
            decision = PromotionDecision.HOLD
            reason = "insufficient sample count"
        elif success_rate < self.policy.minimum_success_rate:
            decision = PromotionDecision.REJECT
            reason = "success rate below promotion threshold"
        elif average_quality < self.policy.minimum_quality_score:
            decision = PromotionDecision.REJECT
            reason = "quality score below promotion threshold"
        else:
            decision = PromotionDecision.PROMOTE
            reason = "candidate meets governed promotion thresholds"

        return SkillCandidate(
            skill_key=skill_key,
            decision=decision,
            sample_count=sample_count,
            success_rate=success_rate,
            average_quality=average_quality,
            evidence_ids=evidence_ids,
            reason=reason,
        )
