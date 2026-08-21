from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ModelCapability(StrEnum):
    CODING = "coding"
    SYSTEM_ENGINEERING = "system_engineering"
    REASONING = "reasoning"
    ABSTRACT_REASONING = "abstract_reasoning"
    MATH = "math"
    MULTIMODAL = "multimodal"
    RESEARCH = "research"
    TOOL_USE = "tool_use"
    LATENCY = "latency"
    COST_EFFICIENCY = "cost_efficiency"


class EvidenceSourceKind(StrEnum):
    PROVIDER = "provider"
    INDEPENDENT = "independent"
    INTERNAL = "internal"


class CapabilityEvidence(BaseModel):
    evidence_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    capability: ModelCapability
    normalized_score: float = Field(ge=0, le=1)
    source_kind: EvidenceSourceKind
    source_ref: str = Field(min_length=1)
    observed_at: datetime
    expires_at: datetime | None = None
    verified: bool = False

    def is_current(self, *, now: datetime) -> bool:
        current = _normalize(now)
        observed = _normalize(self.observed_at)
        if observed > current:
            return False
        if self.expires_at is None:
            return True
        return _normalize(self.expires_at) >= current


class ModelCapabilityProfile(BaseModel):
    model_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    evidence: list[CapabilityEvidence] = Field(default_factory=list)

    def capability_score(
        self,
        capability: ModelCapability,
        *,
        now: datetime,
        require_verified: bool = True,
    ) -> float | None:
        usable = [
            item
            for item in self.evidence
            if item.capability == capability
            and item.is_current(now=now)
            and (item.verified or not require_verified)
        ]
        if not usable:
            return None
        weights = {
            EvidenceSourceKind.PROVIDER: 1.0,
            EvidenceSourceKind.INDEPENDENT: 1.15,
            EvidenceSourceKind.INTERNAL: 1.25,
        }
        weighted_sum = sum(
            item.normalized_score * weights[item.source_kind] for item in usable
        )
        total_weight = sum(weights[item.source_kind] for item in usable)
        return weighted_sum / total_weight


def _normalize(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("evidence timestamps must be timezone-aware")
    return value.astimezone(UTC)
