from __future__ import annotations

from typing import Protocol

from .models import CognitiveRequest, ProviderCapabilities, ProviderResponse


class CognitiveProvider(Protocol):
    name: str

    async def generate(self, request: CognitiveRequest) -> ProviderResponse: ...

    async def stream(self, request: CognitiveRequest): ...

    async def health(self) -> dict[str, object]: ...

    async def capabilities(self) -> ProviderCapabilities: ...

    async def estimate_cost(self, request: CognitiveRequest) -> float: ...
