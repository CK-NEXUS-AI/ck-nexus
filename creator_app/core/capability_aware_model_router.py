from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from creator_app.core.model_capability_evidence import (
    ModelCapability,
    ModelCapabilityProfile,
)


class CapabilityWeight(BaseModel):
    capability: ModelCapability
    weight: float = Field(gt=0, le=1)
    minimum_score: float = Field(default=0.0, ge=0, le=1)


class ModelRoutingRequest(BaseModel):
    task_id: str = Field(min_length=1)
    requirements: list[CapabilityWeight] = Field(min_length=1)
    minimum_evidence_capabilities: int = Field(default=1, ge=1)
    prefer_provider_diversity: bool = True


class ModelRouteCandidate(BaseModel):
    model_id: str
    provider: str
    score: float = Field(ge=0, le=1)
    evidence_capabilities: int = Field(ge=0)
    missing_capabilities: list[ModelCapability] = Field(default_factory=list)


class ModelRoutingDecision(BaseModel):
    task_id: str
    primary: ModelRouteCandidate
    fallbacks: list[ModelRouteCandidate] = Field(default_factory=list)
    independent_verifier: ModelRouteCandidate | None = None


class CapabilityAwareModelRouter:
    """Ranks provider-neutral model profiles using current verified evidence only."""

    def __init__(self) -> None:
        self._profiles: dict[str, ModelCapabilityProfile] = {}

    def register(self, profile: ModelCapabilityProfile) -> None:
        self._profiles[profile.model_id] = profile.model_copy(deep=True)

    def route(
        self,
        request: ModelRoutingRequest,
        *,
        now: datetime,
    ) -> ModelRoutingDecision:
        candidates = [
            candidate
            for profile in self._profiles.values()
            if (candidate := self._score(profile, request, now=now)) is not None
        ]
        if not candidates:
            raise LookupError("no model has sufficient current verified capability evidence")

        ranked = sorted(candidates, key=lambda item: (-item.score, item.model_id))
        primary = ranked[0]
        fallbacks = ranked[1:]

        verifier = None
        if request.prefer_provider_diversity:
            verifier = next(
                (item for item in fallbacks if item.provider != primary.provider),
                None,
            )

        return ModelRoutingDecision(
            task_id=request.task_id,
            primary=primary,
            fallbacks=fallbacks,
            independent_verifier=verifier,
        )

    @staticmethod
    def _score(
        profile: ModelCapabilityProfile,
        request: ModelRoutingRequest,
        *,
        now: datetime,
    ) -> ModelRouteCandidate | None:
        weighted = 0.0
        total_weight = 0.0
        evidence_count = 0
        missing: list[ModelCapability] = []

        for requirement in request.requirements:
            score = profile.capability_score(requirement.capability, now=now)
            if score is None:
                missing.append(requirement.capability)
                continue
            if score < requirement.minimum_score:
                return None
            weighted += score * requirement.weight
            total_weight += requirement.weight
            evidence_count += 1

        if evidence_count < request.minimum_evidence_capabilities or total_weight == 0:
            return None

        return ModelRouteCandidate(
            model_id=profile.model_id,
            provider=profile.provider,
            score=weighted / total_weight,
            evidence_capabilities=evidence_count,
            missing_capabilities=missing,
        )
