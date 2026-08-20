import pytest

from creator_app.ai_gateway import (
    AIGateway,
    CallbackProviderAdapter,
    CapabilityInventory,
    GatewayRequest,
    GlobalCapabilityCatalog,
    ModelCapability,
    ModelDescriptor,
    NoEligibleModel,
    ProviderSnapshot,
    ProviderStage,
)


def _provider(provider_id: str, *models: ModelDescriptor) -> CallbackProviderAdapter:
    return CallbackProviderAdapter(
        provider_id=provider_id,
        discoverer=lambda: ProviderSnapshot(provider_id, True, tuple(models)),
        invoker=lambda model_id, prompt: f"{provider_id}:{model_id}:{prompt}",
    )


def test_catalog_covers_global_provider_families_without_production_claim() -> None:
    catalog = GlobalCapabilityCatalog()

    assert len(catalog.list()) >= 16
    assert len(ModelCapability) >= 30
    assert all(item.production_evidence is False for item in catalog.list())
    assert all(item.classification == "DECLARED_ONLY" for item in catalog.list())


def test_computer_use_is_discovery_only_until_runtime_adapter_proves_it() -> None:
    catalog = GlobalCapabilityCatalog()
    discovered = catalog.discover(frozenset({ModelCapability.COMPUTER_USE}))

    provider_ids = {item.provider_id for item in discovered}
    assert {"openai", "anthropic", "google"}.issubset(provider_ids)

    inventory = CapabilityInventory(catalog).reconcile(AIGateway())
    openai = next(item for item in inventory if item.provider_id == "openai")
    assert openai.stage is ProviderStage.DISCOVERED
    assert openai.runtime_capabilities == frozenset()
    assert openai.production_evidence is False


def test_inventory_separates_declared_from_runtime_capability() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "openai",
            ModelDescriptor(
                "openai",
                "runtime-model",
                frozenset({ModelCapability.TEXT, ModelCapability.REASONING}),
            ),
        )
    )

    records = CapabilityInventory().reconcile(gateway)
    openai = next(item for item in records if item.provider_id == "openai")

    assert openai.stage is ProviderStage.AVAILABLE
    assert ModelCapability.REASONING in openai.active_declared_capabilities
    assert ModelCapability.DEEP_RESEARCH not in openai.active_declared_capabilities


def test_context_requirement_fails_closed_when_metadata_is_unknown() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor("cloud", "unknown-context", frozenset({ModelCapability.TEXT})),
        )
    )

    with pytest.raises(NoEligibleModel):
        gateway.route(
            GatewayRequest(
                "long task",
                frozenset({ModelCapability.TEXT}),
                allow_external=True,
                min_context_window_tokens=100_000,
            )
        )


def test_streaming_and_free_tier_require_explicit_runtime_metadata() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor(
                "cloud",
                "verified-metadata",
                frozenset({ModelCapability.TEXT}),
                context_window_tokens=200_000,
                streaming=True,
                free_tier=True,
            ),
        )
    )

    selected = gateway.route(
        GatewayRequest(
            "hello",
            frozenset({ModelCapability.TEXT}),
            allow_external=True,
            min_context_window_tokens=100_000,
            require_streaming=True,
            require_free_tier=True,
        )
    )

    assert selected.model_id == "verified-metadata"


def test_open_weight_preference_is_policy_not_execution_authority() -> None:
    gateway = AIGateway()
    gateway.register(
        _provider(
            "cloud",
            ModelDescriptor(
                "cloud",
                "closed",
                frozenset({ModelCapability.TEXT}),
                open_weight=False,
            ),
            ModelDescriptor(
                "cloud",
                "open",
                frozenset({ModelCapability.TEXT}),
                open_weight=True,
            ),
        )
    )

    selected = gateway.route(
        GatewayRequest(
            "hello",
            frozenset({ModelCapability.TEXT}),
            allow_external=True,
            prefer_open_weight=True,
        )
    )

    assert selected.model_id == "open"
