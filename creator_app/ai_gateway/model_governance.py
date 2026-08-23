"""Fail-closed model governance for frontier/open-weight providers.

This module does not execute models. It classifies model risk and determines whether a
model is eligible for a requested use lane. CK-NEXUS remains the authority for policy,
permissions, execution and evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import AttestationState, ModelDescriptor, ModelRiskClass


class ModelUseLane(StrEnum):
    DEVELOPMENT = "development"
    EVALUATION = "evaluation"
    RED_TEAM = "red_team"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ModelPolicyDecision:
    allowed: bool
    lane: ModelUseLane
    effective_risk: ModelRiskClass
    quarantine_required: bool
    reason: str


_SAFETY_MODIFIED_MARKERS = (
    "abliterated",
    "obliterated",
    "uncensored",
    "no-refusal",
    "no_refusal",
)


def infer_effective_risk(model: ModelDescriptor) -> ModelRiskClass:
    """Conservatively raise risk from explicit metadata and model identity markers."""

    identity = " ".join(
        (
            model.model_id,
            model.provenance.model_repo,
            model.provenance.modifier,
        )
    ).lower()
    if any(marker in identity for marker in _SAFETY_MODIFIED_MARKERS):
        return ModelRiskClass.SAFETY_MODIFIED
    return model.risk_class


def authorize_model_use(model: ModelDescriptor, lane: ModelUseLane) -> ModelPolicyDecision:
    """Return a deterministic fail-closed eligibility decision.

    Safety-modified, red-team-only and untrusted-weight models are restricted to the
    RED_TEAM lane. Production additionally requires verified model attestation.
    """

    risk = infer_effective_risk(model)
    restricted = {
        ModelRiskClass.RED_TEAM_ONLY,
        ModelRiskClass.SAFETY_MODIFIED,
        ModelRiskClass.UNTRUSTED_WEIGHTS,
    }

    if risk in restricted and lane is not ModelUseLane.RED_TEAM:
        return ModelPolicyDecision(
            allowed=False,
            lane=lane,
            effective_risk=risk,
            quarantine_required=True,
            reason="restricted model risk class is permitted only in the red-team lane",
        )

    if lane is ModelUseLane.PRODUCTION:
        if model.provenance.attestation is not AttestationState.VERIFIED:
            return ModelPolicyDecision(
                allowed=False,
                lane=lane,
                effective_risk=risk,
                quarantine_required=False,
                reason="production requires verified model provenance attestation",
            )
        if not model.provenance.revision_sha or not model.provenance.weight_digest:
            return ModelPolicyDecision(
                allowed=False,
                lane=lane,
                effective_risk=risk,
                quarantine_required=False,
                reason="production requires revision_sha and weight_digest",
            )

    return ModelPolicyDecision(
        allowed=True,
        lane=lane,
        effective_risk=risk,
        quarantine_required=risk in restricted,
        reason="model is eligible for the requested lane",
    )
