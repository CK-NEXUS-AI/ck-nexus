from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrchestrationMode(str, Enum):
    SINGLE_BEST = "single_best"
    PARALLEL = "parallel"
    COUNCIL = "council"
    DEBATE = "debate"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class CognitiveRequest:
    request_id: str
    correlation_id: str
    tenant_id: str
    actor_id: str
    prompt: str
    role: str = "general"
    mode: OrchestrationMode = OrchestrationMode.SINGLE_BEST
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderCapabilities:
    text: bool = True
    vision: bool = False
    streaming: bool = True
    tool_calling: bool = False
    structured_output: bool = False
    embeddings: bool = False


@dataclass
class ProviderResponse:
    provider: str
    model: str
    content: str
    latency_ms: int
    cost_usd: float = 0.0
    citations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
