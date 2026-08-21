from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SkillCandidateStatus(StrEnum):
    CANDIDATE = "candidate"
    REVIEWING = "reviewing"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ExperienceRecord(BaseModel):
    experience_id: str
    workflow_fingerprint: str
    success: bool
    quality_score: float = Field(default=1.0, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)


class SkillLearningPolicy(BaseModel):
    minimum_successes: int = Field(default=3, ge=2)
    minimum_average_quality: float = Field(default=0.75, ge=0, le=1)
    minimum_distinct_evidence: int = Field(default=2, ge=1)


class SkillCandidate(BaseModel):
    skill_id: str
    workflow_fingerprint: str
    occurrences: int = Field(ge=1)
    average_quality: float = Field(default=1.0, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    allowed_tools: set[str] = Field(default_factory=set)
    status: SkillCandidateStatus = SkillCandidateStatus.CANDIDATE
    production_activation_allowed: bool = False


class ExperienceSkillLearner:
    """Derives non-active skill candidates from repeated successful workflows."""

    def __init__(self, policy: SkillLearningPolicy | None = None) -> None:
        self.policy = policy or SkillLearningPolicy()

    def propose(
        self,
        *,
        skill_id: str,
        experiences: list[ExperienceRecord],
        minimum_successes: int | None = None,
        allowed_tools: set[str] | None = None,
    ) -> SkillCandidate:
        required_successes = minimum_successes or self.policy.minimum_successes
        if required_successes < 2:
            raise ValueError("minimum_successes must be at least 2")
        successful = [item for item in experiences if item.success]
        if len(successful) < required_successes:
            raise ValueError("insufficient successful experiences for skill candidate")
        fingerprints = {item.workflow_fingerprint for item in successful}
        if len(fingerprints) != 1:
            raise ValueError("experiences do not represent one stable workflow")
        if any(not item.evidence_ids for item in successful):
            raise ValueError("successful experience requires evidence")
        evidence_ids = sorted({eid for item in successful for eid in item.evidence_ids})
        if len(evidence_ids) < self.policy.minimum_distinct_evidence:
            raise ValueError("insufficient distinct evidence for skill candidate")
        average_quality = sum(item.quality_score for item in successful) / len(successful)
        if average_quality < self.policy.minimum_average_quality:
            raise ValueError("average quality below skill candidate threshold")
        return SkillCandidate(
            skill_id=skill_id,
            workflow_fingerprint=successful[0].workflow_fingerprint,
            occurrences=len(successful),
            average_quality=average_quality,
            evidence_ids=evidence_ids,
            allowed_tools=allowed_tools or set(),
        )

    def mark_verified(
        self,
        candidate: SkillCandidate,
        *,
        verifier_evidence_id: str,
    ) -> SkillCandidate:
        if not verifier_evidence_id:
            raise ValueError("verifier evidence is required")
        updated = candidate.model_copy(deep=True)
        updated.evidence_ids = sorted({*updated.evidence_ids, verifier_evidence_id})
        updated.status = SkillCandidateStatus.VERIFIED
        updated.production_activation_allowed = False
        return updated
