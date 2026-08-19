"""Dynamic, capability-based AI provider routing for CK-NEXUS."""

from __future__ import annotations

import hashlib
import json

from .contracts import AIProvider, DataClass, GatewayRequest, GatewayResponse, ModelDescriptor


class NoEligibleModel(RuntimeError):
    """Raised when policy leaves no model eligible for a request."""


class AIGateway:
    """Route by capability and policy instead of hard-coded model names."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        provider_id = provider.provider_id.strip()
        if not provider_id:
            raise ValueError("provider_id must not be empty")
        if provider_id in self._providers:
            raise ValueError(f"provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def discover(self) -> dict[str, tuple[ModelDescriptor, ...]]:
        """Refresh catalogs from adapters; unhealthy adapters contribute no models."""
        result: dict[str, tuple[ModelDescriptor, ...]] = {}
        for provider_id, provider in sorted(self._providers.items()):
            snapshot = provider.discover_models()
            if snapshot.provider_id != provider_id:
                raise ValueError("provider snapshot identity mismatch")
            result[provider_id] = snapshot.models if snapshot.healthy else ()
        return result

    def route(self, request: GatewayRequest) -> ModelDescriptor:
        candidates: list[ModelDescriptor] = []
        catalogs = self.discover()
        for provider_id, models in catalogs.items():
            if request.allowed_providers and provider_id not in request.allowed_providers:
                continue
            if provider_id in request.denied_providers:
                continue
            for model in models:
                if not request.required_capabilities.issubset(model.capabilities):
                    continue
                if model.cost_tier > request.max_cost_tier:
                    continue
                if request.data_class in {DataClass.PERSONAL, DataClass.SENSITIVE}:
                    if not model.local and not request.allow_external:
                        continue
                candidates.append(model)

        if not candidates:
            raise NoEligibleModel("no model satisfies capability, privacy and cost policy")

        def score(model: ModelDescriptor) -> tuple[int, int, int, str, str]:
            local_penalty = 0 if (request.prefer_local and model.local) else 1
            return (
                local_penalty,
                model.cost_tier,
                model.latency_tier,
                model.provider_id,
                model.model_id,
            )

        return min(candidates, key=score)

    def invoke(self, request: GatewayRequest) -> GatewayResponse:
        selected = self.route(request)
        provider = self._providers[selected.provider_id]
        output = provider.invoke(selected.model_id, request.prompt)
        evidence_payload = {
            "provider_id": selected.provider_id,
            "model_id": selected.model_id,
            "required_capabilities": sorted(item.value for item in request.required_capabilities),
            "data_class": request.data_class.value,
            "external_allowed": request.allow_external,
            "selected_local": selected.local,
            "max_cost_tier": request.max_cost_tier,
            "authority": "CK-NEXUS",
            "credential_material_in_route": False,
            "model_catalog_source": "runtime_adapter_discovery",
        }
        encoded = json.dumps(evidence_payload, sort_keys=True, separators=(",", ":")).encode()
        evidence = {
            **evidence_payload,
            "route_digest": hashlib.sha256(encoded).hexdigest(),
        }
        return GatewayResponse(
            provider_id=selected.provider_id,
            model_id=selected.model_id,
            output=output,
            route_evidence=evidence,
        )

    def status(self) -> dict[str, object]:
        return {
            "registered_providers": sorted(self._providers),
            "provider_count": len(self._providers),
            "authority": "CK-NEXUS",
            "hard_coded_model_inventory": False,
        }
