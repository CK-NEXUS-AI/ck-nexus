from __future__ import annotations

from dataclasses import dataclass

from .base import CognitiveProvider
from .models import CognitiveRequest, ProviderCapabilities


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    reason: str


class CognitiveRouter:
    def __init__(self) -> None:
        self._providers: dict[str, CognitiveProvider] = {}

    def register(self, provider: CognitiveProvider) -> None:
        self._providers[provider.name] = provider

    async def select(self, request: CognitiveRequest) -> tuple[CognitiveProvider, RouteDecision]:
        if not self._providers:
            raise RuntimeError("no cognitive providers registered")

        preferred = request.metadata.get("preferred_provider")
        if isinstance(preferred, str) and preferred in self._providers:
            return self._providers[preferred], RouteDecision(preferred, "explicit preference")

        for provider in self._providers.values():
            caps: ProviderCapabilities = await provider.capabilities()
            if request.role == "vision" and not caps.vision:
                continue
            return provider, RouteDecision(provider.name, "first compatible provider")

        raise RuntimeError("no compatible cognitive provider")
