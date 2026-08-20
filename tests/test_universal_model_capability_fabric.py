from dataclasses import dataclass

from creator_app.model_fabric import (
    CapabilityEvidence,
    CapabilityRequirement,
    ModelCapability,
    ModelCapabilityResolver,
    ModelProviderCatalog,
    RuntimeProviderSnapshot,
    runtime_snapshot_from_router_status,
)


@dataclass(frozen=True)
class _Capabilities:
    features: frozenset[str]


@dataclass(frozen=True)
class _Status:
    name: str
    available: bool
    circuit_open: bool
    capabilities: _Capabilities
    kind: object = "cloud"


def test_catalog_has_global_provider_coverage_without_production_claims() -> None:
    catalog = ModelProviderCatalog()
    profiles = catalog.list()

    assert len(profiles) >= 16
    assert all(profile.evidence is CapabilityEvidence.DECLARED_ONLY for profile in profiles)
    assert all(profile.production_evidence is False for profile in profiles)


def test_computer_use_discovery_is_not_execution_authority() -> None:
    resolver = ModelCapabilityResolver()
    requirement = CapabilityRequirement.of(ModelCapability.COMPUTER_USE)

    discovered = resolver.discover(requirement)
    assessed = resolver.assess(requirement)

    ids = {profile.provider_id for profile in discovered}
    assert {"openai", "anthropic", "google"}.issubset(ids)
    assert assessed
    assert all(item.eligible_for_execution is False for item in assessed)
    assert all("DISCOVERED_NOT_CONNECTED" in item.reasons for item in assessed)


def test_router_status_translation_is_conservative() -> None:
    snapshot = runtime_snapshot_from_router_status(
        _Status(
            name="openai",
            available=True,
            circuit_open=False,
            capabilities=_Capabilities(features=frozenset({"text", "web-search"})),
        )
    )

    assert snapshot.runtime_capabilities == frozenset({ModelCapability.REASONING})
    assert ModelCapability.DEEP_RESEARCH not in snapshot.runtime_capabilities
    assert snapshot.independently_verified is False


def test_exact_runtime_capability_can_become_execution_eligible() -> None:
    resolver = ModelCapabilityResolver()
    requirement = CapabilityRequirement.of(ModelCapability.REASONING)
    runtime = (
        RuntimeProviderSnapshot(
            provider_id="openai",
            connected=True,
            available=True,
            circuit_open=False,
            runtime_capabilities=frozenset({ModelCapability.REASONING}),
        ),
    )

    eligible = resolver.eligible(requirement, runtime)

    assert [item.provider.provider_id for item in eligible] == ["openai"]
    assert eligible[0].independently_verified is False
    assert "ELIGIBLE_RUNTIME_CAPABILITY" in eligible[0].reasons


def test_runtime_missing_exact_capability_fails_closed() -> None:
    resolver = ModelCapabilityResolver()
    requirement = CapabilityRequirement.of(ModelCapability.DEEP_RESEARCH)
    runtime = (
        RuntimeProviderSnapshot(
            provider_id="openai",
            connected=True,
            available=True,
            circuit_open=False,
            runtime_capabilities=frozenset({ModelCapability.REASONING}),
        ),
    )

    assessed = resolver.assess(requirement, runtime)
    openai = next(item for item in assessed if item.provider.provider_id == "openai")

    assert openai.eligible_for_execution is False
    assert "RUNTIME_CAPABILITY_NOT_VERIFIED" in openai.reasons


def test_local_only_requirement_does_not_promote_model_vendors() -> None:
    resolver = ModelCapabilityResolver()
    requirement = CapabilityRequirement.of(
        ModelCapability.LOCAL_MODEL_RUNTIME,
        local_only=True,
    )

    discovered = resolver.discover(requirement)

    assert [profile.provider_id for profile in discovered] == ["ollama"]
