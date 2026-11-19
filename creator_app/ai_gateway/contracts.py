"""Provider-agnostic contracts for the CK-NEXUS capability AI gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class ModelCapability(StrEnum):
    TEXT = "text"
    REASONING = "reasoning"
    CODE = "code"
    VISION = "vision"
    AUDIO = "audio"
    TOOL_USE = "tool_use"
    EMBEDDINGS = "embeddings"
    LOCAL = "local"


class DataClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    provider_id: str
    model_id: str
    capabilities: frozenset[ModelCapability]
    cost_tier: int = 1
    latency_tier: int = 1
    local: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise ValueError("provider_id and model_id must not be empty")
        if not 0 <= self.cost_tier <= 5 or not 0 <= self.latency_tier <= 5:
            raise ValueError("cost_tier and latency_tier must be between 0 and 5")


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    provider_id: str
    healthy: bool
    models: tuple[ModelDescriptor, ...]
    source: str = "live_discovery"
    refreshed_at: str = ""

    def __post_init__(self) -> None:
        if not self.refreshed_at:
            object.__setattr__(self, "refreshed_at", datetime.now(UTC).isoformat())
        if any(model.provider_id != self.provider_id for model in self.models):
            raise ValueError("snapshot contains a model from another provider")


@dataclass(frozen=True, slots=True)
class GatewayRequest:
    prompt: str
    required_capabilities: frozenset[ModelCapability]
    data_class: DataClass = DataClass.INTERNAL
    allow_external: bool = False
    max_cost_tier: int = 5
    prefer_local: bool = False
    allowed_providers: frozenset[str] = frozenset()
    denied_providers: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if not 0 <= self.max_cost_tier <= 5:
            raise ValueError("max_cost_tier must be between 0 and 5")


@dataclass(frozen=True, slots=True)
class GatewayResponse:
    provider_id: str
    model_id: str
    output: str
    route_evidence: dict[str, Any]


class AIProvider(Protocol):
    """Adapter boundary. Providers discover their current model catalog at runtime."""

    @property
    def provider_id(self) -> str: ...

    def discover_models(self) -> ProviderSnapshot: ...

    def invoke(self, model_id: str, prompt: str) -> str: ...
