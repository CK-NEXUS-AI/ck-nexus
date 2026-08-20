from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from creator_app.model_fabric.capabilities import CapabilityRequirement, ModelCapability
from creator_app.model_fabric.catalog import ModelProviderCatalog, ProviderCapabilityProfile


class RouterStatusLike(Protocol):
    name: str
    available: bool
    circuit_open: bool
    kind: object
    capabilities: object


@dataclass(frozen=True, slots=True)
class RuntimeProviderSnapshot:
    provider_id: str
    connected: bool
    available: bool
    circuit_open: bool
    runtime_capabilities: frozenset[ModelCapability]
    source: str = "provider_router.statuses"
    independently_verified: bool = False


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    provider: ProviderCapabilityProfile
    connected: bool
    available: bool
    runtime_supports: bool
    eligible_for_execution: bool
    independently_verified: bool
    reasons: tuple[str, ...]


_RUNTIME_FEATURE_MAP: dict[str, frozenset[ModelCapability]] = {
    "text": frozenset({ModelCapability.REASONING}),
    "local": frozenset({ModelCapability.LOCAL_MODEL_RUNTIME}),
}


def runtime_snapshot_from_router_status(status: RouterStatusLike) -> RuntimeProviderSnapshot:
    """Translate canonical ProviderRouter status without inflating capabilities.

    Only conservative feature aliases are mapped. Catalog declarations are not
    copied into runtime state, so discovery can never silently become execution
    authority.
    """

    features = getattr(status.capabilities, "features", frozenset())
    normalized: set[ModelCapability] = set()
    for feature in features:
        normalized.update(_RUNTIME_FEATURE_MAP.get(str(feature), frozenset()))
    return RuntimeProviderSnapshot(
        provider_id=status.name,
        connected=True,
        available=bool(status.available),
        circuit_open=bool(status.circuit_open),
        runtime_capabilities=frozenset(normalized),
    )


class ModelCapabilityResolver:
    """Resolve provider-neutral capabilities against declared and runtime state.

    The resolver deliberately separates discovery from execution eligibility:
    - catalog declaration => discovered only
    - canonical router status => connected/available
    - exact runtime capability => execution-eligible
    - independent verifier => independently verified
    """

    def __init__(self, catalog: ModelProviderCatalog | None = None) -> None:
        self.catalog = catalog or ModelProviderCatalog()

    def discover(
        self,
        requirement: CapabilityRequirement,
    ) -> tuple[ProviderCapabilityProfile, ...]:
        return self.catalog.discover(
            requirement.required,
            local_only=requirement.local_only,
            allow_gateways=requirement.allow_gateways,
        )

    def assess(
        self,
        requirement: CapabilityRequirement,
        runtime: tuple[RuntimeProviderSnapshot, ...] = (),
    ) -> tuple[CapabilityResolution, ...]:
        runtime_by_id = {item.provider_id: item for item in runtime}
        resolutions: list[CapabilityResolution] = []

        for profile in self.discover(requirement):
            snapshot = runtime_by_id.get(profile.provider_id)
            connected = snapshot is not None and snapshot.connected
            available = bool(snapshot and snapshot.available and not snapshot.circuit_open)
            runtime_supports = bool(
                snapshot
                and requirement.required.issubset(snapshot.runtime_capabilities)
            )
            eligible = connected and available and runtime_supports
            reasons: list[str] = []

            if not connected:
                reasons.append("DISCOVERED_NOT_CONNECTED")
            elif snapshot is not None and snapshot.circuit_open:
                reasons.append("CIRCUIT_OPEN")
            elif not available:
                reasons.append("CONNECTED_NOT_AVAILABLE")

            if connected and not runtime_supports:
                reasons.append("RUNTIME_CAPABILITY_NOT_VERIFIED")
            if eligible:
                reasons.append("ELIGIBLE_RUNTIME_CAPABILITY")

            resolutions.append(
                CapabilityResolution(
                    provider=profile,
                    connected=connected,
                    available=available,
                    runtime_supports=runtime_supports,
                    eligible_for_execution=eligible,
                    independently_verified=bool(
                        snapshot and snapshot.independently_verified
                    ),
                    reasons=tuple(reasons),
                )
            )

        return tuple(resolutions)

    def eligible(
        self,
        requirement: CapabilityRequirement,
        runtime: tuple[RuntimeProviderSnapshot, ...],
    ) -> tuple[CapabilityResolution, ...]:
        return tuple(
            item
            for item in self.assess(requirement, runtime)
            if item.eligible_for_execution
        )
