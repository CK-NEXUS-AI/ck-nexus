from datetime import UTC, datetime, timedelta

import pytest

from creator_app.core.capability_aware_model_router import (
    CapabilityAwareModelRouter,
    CapabilityWeight,
    ModelRoutingRequest,
)
from creator_app.core.model_capability_evidence import (
    CapabilityEvidence,
    EvidenceSourceKind,
    ModelCapability,
    ModelCapabilityProfile,
)

NOW = datetime(2026, 8, 21, 11, tzinfo=UTC)


def evidence(
    evidence_id: str,
    model_id: str,
    capability: ModelCapability,
    score: float,
    *,
    provider_self_reported: bool = False,
    verified: bool = True,
    expired: bool = False,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        evidence_id=evidence_id,
        model_id=model_id,
        capability=capability,
        normalized_score=score,
        source_kind=(
            EvidenceSourceKind.PROVIDER
            if provider_self_reported
            else EvidenceSourceKind.INDEPENDENT
        ),
        source_ref=f"ref:{evidence_id}",
        observed_at=NOW - timedelta(days=1),
        expires_at=NOW - timedelta(seconds=1) if expired else NOW + timedelta(days=30),
        verified=verified,
    )


def test_routes_coding_task_to_best_verified_profile() -> None:
    router = CapabilityAwareModelRouter()
    router.register(
        ModelCapabilityProfile(
            model_id="model-a",
            provider="provider-a",
            evidence=[evidence("a-code", "model-a", ModelCapability.CODING, 0.91)],
        )
    )
    router.register(
        ModelCapabilityProfile(
            model_id="model-b",
            provider="provider-b",
            evidence=[evidence("b-code", "model-b", ModelCapability.CODING, 0.82)],
        )
    )

    decision = router.route(
        ModelRoutingRequest(
            task_id="task:code",
            requirements=[CapabilityWeight(capability=ModelCapability.CODING, weight=1.0)],
        ),
        now=NOW,
    )

    assert decision.primary.model_id == "model-a"
    assert decision.independent_verifier is not None
    assert decision.independent_verifier.provider == "provider-b"


def test_unverified_or_expired_evidence_is_not_usable() -> None:
    profile = ModelCapabilityProfile(
        model_id="model-a",
        provider="provider-a",
        evidence=[
            evidence(
                "unverified",
                "model-a",
                ModelCapability.REASONING,
                1.0,
                verified=False,
            ),
            evidence(
                "expired",
                "model-a",
                ModelCapability.REASONING,
                1.0,
                expired=True,
            ),
        ],
    )

    assert profile.capability_score(ModelCapability.REASONING, now=NOW) is None


def test_minimum_capability_threshold_fails_closed() -> None:
    router = CapabilityAwareModelRouter()
    router.register(
        ModelCapabilityProfile(
            model_id="model-a",
            provider="provider-a",
            evidence=[evidence("reason", "model-a", ModelCapability.REASONING, 0.7)],
        )
    )

    with pytest.raises(LookupError):
        router.route(
            ModelRoutingRequest(
                task_id="task:reason",
                requirements=[
                    CapabilityWeight(
                        capability=ModelCapability.REASONING,
                        weight=1.0,
                        minimum_score=0.8,
                    )
                ],
            ),
            now=NOW,
        )


def test_multi_capability_task_uses_weighted_score() -> None:
    router = CapabilityAwareModelRouter()
    router.register(
        ModelCapabilityProfile(
            model_id="engineer",
            provider="provider-a",
            evidence=[
                evidence("c1", "engineer", ModelCapability.CODING, 0.95),
                evidence("r1", "engineer", ModelCapability.REASONING, 0.72),
            ],
        )
    )
    router.register(
        ModelCapabilityProfile(
            model_id="reasoner",
            provider="provider-b",
            evidence=[
                evidence("c2", "reasoner", ModelCapability.CODING, 0.78),
                evidence("r2", "reasoner", ModelCapability.REASONING, 0.96),
            ],
        )
    )

    decision = router.route(
        ModelRoutingRequest(
            task_id="task:system-design",
            minimum_evidence_capabilities=2,
            requirements=[
                CapabilityWeight(capability=ModelCapability.CODING, weight=0.7),
                CapabilityWeight(capability=ModelCapability.REASONING, weight=0.3),
            ],
        ),
        now=NOW,
    )

    assert decision.primary.model_id == "engineer"


def test_provider_claim_can_contribute_but_not_bypass_verification() -> None:
    profile = ModelCapabilityProfile(
        model_id="model-a",
        provider="provider-a",
        evidence=[
            evidence(
                "provider",
                "model-a",
                ModelCapability.MATH,
                0.99,
                provider_self_reported=True,
                verified=False,
            ),
            evidence("independent", "model-a", ModelCapability.MATH, 0.8),
        ],
    )

    assert profile.capability_score(ModelCapability.MATH, now=NOW) == pytest.approx(0.8)
