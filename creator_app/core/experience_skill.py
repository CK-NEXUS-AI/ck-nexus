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
    evidence_ids: list[str] = Field(default_factory=list)


class SkillCandidate(BaseModel):
    skill_id: str
    workflow_fingerprint: str
    occurrences: int = Field(ge=1)
    evidence_ids: list[str] = Field(default_factory=list)
    allowed_tools: set[str] = Field(default_factory=set)
    status: SkillCandidateStatus = SkillCandidateStatus.CANDIDATE
    production_activation_allowed: bool = False


class ExperienceSkillLearner:
    """Derives non-active skill candidates from repeated successful workflows."""

    def propose(
        self,
        *,
        skill_id: str,
        experiences: list[ExperienceRecord],
        minimum_successes: int = 3,
        allowed_tools: set[str] | None = None,
    ) -> SkillCandidate:
        if minimum_successes < 2:
            raise ValueError("minimum_successes must be at least 2")
        successful = [item for item in experiences if item.success]
        if len(successful) < minimum_successes:
            raise ValueError("insufficient successful experiences for skill candidate")
        fingerprints = {item.workflow_fingerprint for item in successful}
        if len(fingerprints) != 1:
            raise ValueError("experiences do not represent one stable workflow")
        evidence_ids = sorted({eid for item in successful for eid in item.evidence_ids})
        if not evidence_ids:
            raise ValueError("skill candidate requires evidence")
        return SkillCandidate(
            skill_id=skill_id,
            workflow_fingerprint=successful[0].workflow_fingerprint,
            occurrences=len(successful),
            evidence_ids=evidence_ids,
            allowed_tools=allowed_tools or set(),
        )

    def mark_verified(self, candidate: SkillCandidate, *, verifier_evidence_id: str) -> SkillCandidate:
        if not verifier_evidence_id:
            raise ValueError("verifier evidence is required")
        updated = candidate.model_copy(deep=True)
        updated.evidence_ids = sorted({*updated.evidence_ids, verifier_evidence_id})
        updated.status = SkillCandidateStatus.VERIFIED
        updated.production_activation_allowed = False
        return updated
