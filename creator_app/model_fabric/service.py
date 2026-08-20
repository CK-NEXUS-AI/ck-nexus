from __future__ import annotations

from typing import Protocol

from creator_app.model_fabric.capabilities import CapabilityRequirement, ModelCapability
from creator_app.model_fabric.resolver import (
    CapabilityResolution,
    ModelCapabilityResolver,
    RuntimeProviderSnapshot,
    runtime_snapshot_from_router_status,
)


class ProviderRouterLike(Protocol):
    def statuses(self) -> tuple[object, ...]: ...


class UniversalModelCapabilityFabric:
    """Read-only capability view over the canonical CK-NEXUS ProviderRouter.

    This component intentionally does not own credentials, execute prompts, or
    mutate router circuit state. Execution continues through the canonical
    ProviderRouter and CredentialBroker paths.
    """

    def __init__(
        self,
        router: ProviderRouterLike,
        *,
        resolver: ModelCapabilityResolver | None = None,
    ) -> None:
        self.router = router
        self.resolver = resolver or ModelCapabilityResolver()

    def runtime_snapshots(self) -> tuple[RuntimeProviderSnapshot, ...]:
        return tuple(
            runtime_snapshot_from_router_status(status)  # type: ignore[arg-type]
            for status in self.router.statuses()
        )

    def assess(
        self,
        *capabilities: ModelCapability,
        local_only: bool = False,
        allow_gateways: bool = True,
    ) -> tuple[CapabilityResolution, ...]:
        requirement = CapabilityRequirement.of(
            *capabilities,
            local_only=local_only,
            allow_gateways=allow_gateways,
        )
        return self.resolver.assess(requirement, self.runtime_snapshots())

    def eligible(
        self,
        *capabilities: ModelCapability,
        local_only: bool = False,
        allow_gateways: bool = True,
    ) -> tuple[CapabilityResolution, ...]:
        requirement = CapabilityRequirement.of(
            *capabilities,
            local_only=local_only,
            allow_gateways=allow_gateways,
        )
        return self.resolver.eligible(requirement, self.runtime_snapshots())

    def summary(self) -> dict[str, object]:
        profiles = self.resolver.catalog.list()
        snapshots = self.runtime_snapshots()
        connected = {snapshot.provider_id for snapshot in snapshots if snapshot.connected}
        available = {
            snapshot.provider_id
            for snapshot in snapshots
            if snapshot.connected and snapshot.available and not snapshot.circuit_open
        }
        return {
            "component": "universal_model_capability_fabric",
            "classification": "DEVELOPMENT_ONLY",
            "providers_catalogued": len(profiles),
            "providers_connected": len(connected),
            "providers_available": len(available),
            "production_evidence": False,
            "production_promotion_allowed": False,
        }
