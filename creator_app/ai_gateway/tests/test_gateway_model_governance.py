import pytest

from creator_app.ai_gateway import (
    AIGateway,
    AttestationState,
    CallbackProviderAdapter,
    GatewayRequest,
    ModelCapability,
    ModelDescriptor,
    ModelProvenance,
    ModelUseLane,
    NoEligibleModel,
    ProviderSnapshot,
)


def _provider(provider_id: str, *models: ModelDescriptor) -> CallbackProviderAdapter:
    return CallbackProviderAdapter(
        provider_id=provider_id,
        discoverer=lambda: ProviderSnapshot(provider_id, True, tuple(models)),
        invoker=lambda model_id, prompt: f"{provider_id}:{model_id}:{prompt}",
    )


def test_safety_modified_model_is_not_routed_in_development() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "hf",
            ModelDescriptor(
                "hf",
                "OBLITERATUS/Qwen3.8-27B-OBLITERATED",
                frozenset({ModelCapability.TEXT, ModelCapability.RED_TEAM_MODEL}),
            ),
        )
    )
    with pytest.raises(NoEligibleModel, match="model-governance"):
        gateway.route(
            GatewayRequest(
                "test",
                frozenset({ModelCapability.TEXT}),
                allow_external=True,
            )
        )


def test_safety_modified_model_can_route_only_in_red_team_lane() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "hf",
            ModelDescriptor(
                "hf",
                "OBLITERATUS/Qwen3.8-27B-OBLITERATED",
                frozenset({ModelCapability.TEXT, ModelCapability.RED_TEAM_MODEL}),
            ),
        )
    )
    chosen = gateway.route(
        GatewayRequest(
            "adversarial evaluation",
            frozenset({ModelCapability.RED_TEAM_MODEL}),
            allow_external=True,
            model_use_lane=ModelUseLane.RED_TEAM,
        )
    )
    assert chosen.model_id.endswith("OBLITERATED")


def test_production_lane_fails_closed_without_verified_attestation() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "standard",
            ModelDescriptor(
                "standard",
                "model",
                frozenset({ModelCapability.TEXT}),
            ),
        )
    )
    with pytest.raises(NoEligibleModel):
        gateway.route(
            GatewayRequest(
                "production request",
                frozenset({ModelCapability.TEXT}),
                allow_external=True,
                model_use_lane=ModelUseLane.PRODUCTION,
            )
        )


def test_production_lane_accepts_verified_attested_standard_model() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "standard",
            ModelDescriptor(
                "standard",
                "model",
                frozenset({ModelCapability.TEXT}),
                provenance=ModelProvenance(
                    revision_sha="a" * 40,
                    weight_digest="sha256:" + "b" * 64,
                    attestation=AttestationState.VERIFIED,
                ),
            ),
        )
    )
    response = gateway.invoke(
        GatewayRequest(
            "production request",
            frozenset({ModelCapability.TEXT}),
            allow_external=True,
            model_use_lane=ModelUseLane.PRODUCTION,
        )
    )
    assert response.route_evidence["model_attestation"] == "verified"
    assert response.route_evidence["model_use_lane"] == "production"
