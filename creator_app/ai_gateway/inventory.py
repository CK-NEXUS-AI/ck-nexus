"""Reconcile declared provider capabilities with live gateway discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .catalog import GlobalCapabilityCatalog, ProviderCapabilityDeclaration
from .contracts import ModelCapability, ModelDescriptor
from .gateway import AIGateway


class ProviderStage(StrEnum):
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    AVAILABLE = "available"


@dataclass(frozen=True, slots=True)
class ProviderInventoryRecord:
    provider_id: str
    declaration: ProviderCapabilityDeclaration | None
    stage: ProviderStage
    runtime_models: tuple[ModelDescriptor, ...]
    runtime_capabilities: frozenset[ModelCapability]
    production_evidence: bool = False

    @property
    def declared_capabilities(self) -> frozenset[ModelCapability]:
        if self.declaration is None:
            return frozenset()
        return self.declaration.capabilities

    @property
    def active_declared_capabilities(self) -> frozenset[ModelCapability]:
        return self.declared_capabilities.intersection(self.runtime_capabilities)


class CapabilityInventory:
    """Evidence-aware inventory that preserves discovered != connected != active."""

    def __init__(self, catalog: GlobalCapabilityCatalog | None = None) -> None:
        self.catalog = catalog or GlobalCapabilityCatalog()

    def reconcile(self, gateway: AIGateway) -> tuple[ProviderInventoryRecord, ...]:
        runtime = gateway.discover()
        registered = set(gateway.registered_provider_ids())
        declared_ids = {item.provider_id for item in self.catalog.list()}
        provider_ids = sorted(declared_ids.union(runtime))
        records: list[ProviderInventoryRecord] = []

        for provider_id in provider_ids:
            models = runtime.get(provider_id, ())
            runtime_capabilities = frozenset(
                capability
                for model in models
                for capability in model.capabilities
            )
            if models:
                stage = ProviderStage.AVAILABLE
            elif provider_id in registered:
                stage = ProviderStage.REGISTERED
            else:
                stage = ProviderStage.DISCOVERED
            records.append(
                ProviderInventoryRecord(
                    provider_id=provider_id,
                    declaration=self.catalog.get(provider_id),
                    stage=stage,
                    runtime_models=models,
                    runtime_capabilities=runtime_capabilities,
                )
            )

        return tuple(records)

    def summary(self, gateway: AIGateway) -> dict[str, object]:
        records = self.reconcile(gateway)
        return {
            "component": "universal_model_capability_fabric",
            "classification": "DEVELOPMENT_ONLY",
            "providers_catalogued": sum(item.declaration is not None for item in records),
            "providers_registered": sum(
                item.stage in {ProviderStage.REGISTERED, ProviderStage.AVAILABLE}
                for item in records
            ),
            "providers_available": sum(
                item.stage is ProviderStage.AVAILABLE for item in records
            ),
            "production_evidence": False,
            "production_promotion_allowed": False,
        }
