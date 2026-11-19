"""Tests for CK-NEXUS capability AI gateway."""

import pytest

from creator_app.ai_gateway import (
    AIGateway,
    CallbackProviderAdapter,
    DataClass,
    GatewayRequest,
    ModelCapability,
    ModelDescriptor,
    NoEligibleModel,
    ProviderSnapshot,
)


def _provider(
    provider_id: str,
    *models: ModelDescriptor,
    healthy: bool = True,
) -> CallbackProviderAdapter:
    return CallbackProviderAdapter(
        provider_id=provider_id,
        discoverer=lambda: ProviderSnapshot(provider_id, healthy, tuple(models)),
        invoker=lambda model_id, prompt: f"{provider_id}:{model_id}:{prompt}",
    )


def test_gateway_discovers_models_at_runtime() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "provider-a",
            ModelDescriptor(
                "provider-a",
                "runtime-model",
                frozenset({ModelCapability.TEXT}),
            ),
        )
    )
    catalog = gateway.discover()
    assert catalog["provider-a"][0].model_id == "runtime-model"
    assert gateway.status()["hard_coded_model_inventory"] is False


def test_route_selects_required_capability() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "provider-a",
            ModelDescriptor("provider-a", "text", frozenset({ModelCapability.TEXT})),
            ModelDescriptor(
                "provider-a",
                "coder",
                frozenset({ModelCapability.TEXT, ModelCapability.CODE}),
            ),
        )
    )
    chosen = gateway.route(
        GatewayRequest("fix code", frozenset({ModelCapability.CODE}), allow_external=True)
    )
    assert chosen.model_id == "coder"


def test_personal_data_is_local_only_by_default() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor("cloud", "cloud-model", frozenset({ModelCapability.TEXT})),
        )
    )
    with pytest.raises(NoEligibleModel, match="privacy"):
        gateway.route(
            GatewayRequest(
                "personal context",
                frozenset({ModelCapability.TEXT}),
                data_class=DataClass.PERSONAL,
            )
        )


def test_personal_data_can_route_to_local_without_external_consent() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "local",
            ModelDescriptor(
                "local",
                "local-model",
                frozenset({ModelCapability.TEXT, ModelCapability.LOCAL}),
                local=True,
            ),
        )
    )
    chosen = gateway.route(
        GatewayRequest(
            "personal context",
            frozenset({ModelCapability.TEXT}),
            data_class=DataClass.PERSONAL,
            prefer_local=True,
        )
    )
    assert chosen.local is True


def test_explicit_external_allowance_permits_personal_route() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor("cloud", "cloud-model", frozenset({ModelCapability.TEXT})),
        )
    )
    chosen = gateway.route(
        GatewayRequest(
            "authorized personal context",
            frozenset({ModelCapability.TEXT}),
            data_class=DataClass.PERSONAL,
            allow_external=True,
        )
    )
    assert chosen.provider_id == "cloud"


def test_cost_ceiling_is_fail_closed() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor(
                "cloud",
                "expensive",
                frozenset({ModelCapability.REASONING}),
                cost_tier=5,
            ),
        )
    )
    with pytest.raises(NoEligibleModel):
        gateway.route(
            GatewayRequest(
                "reason",
                frozenset({ModelCapability.REASONING}),
                allow_external=True,
                max_cost_tier=2,
            )
        )


def test_denied_provider_is_not_routed() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "blocked",
            ModelDescriptor("blocked", "m", frozenset({ModelCapability.TEXT})),
        )
    )
    with pytest.raises(NoEligibleModel):
        gateway.route(
            GatewayRequest(
                "hello",
                frozenset({ModelCapability.TEXT}),
                allow_external=True,
                denied_providers=frozenset({"blocked"}),
            )
        )


def test_unhealthy_provider_contributes_no_models() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "down",
            ModelDescriptor("down", "m", frozenset({ModelCapability.TEXT})),
            healthy=False,
        )
    )
    assert gateway.discover()["down"] == ()


def test_invoke_records_route_evidence_without_credentials() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "provider-a",
            ModelDescriptor("provider-a", "m", frozenset({ModelCapability.TEXT})),
        )
    )
    response = gateway.invoke(
        GatewayRequest("hello", frozenset({ModelCapability.TEXT}), allow_external=True)
    )
    assert response.output == "provider-a:m:hello"
    assert response.route_evidence["authority"] == "CK-NEXUS"
    assert response.route_evidence["credential_material_in_route"] is False
    assert len(response.route_evidence["route_digest"]) == 64


def test_duplicate_provider_registration_is_rejected() -> None:
    gateway = AIGateway()
    provider = _provider("provider-a")
    gateway.register(provider)
    with pytest.raises(ValueError, match="already registered"):
        gateway.register(provider)
