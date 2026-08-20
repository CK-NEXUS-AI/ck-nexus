"""Provider-agnostic contracts for the CK-NEXUS capability AI gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class ModelCapability(StrEnum):
    TEXT = "text"
    REASONING = "reasoning"
    THINKING = "thinking"
    CODE = "code"
    CODE_REVIEW = "code_review"
    FIM_CODE_COMPLETION = "fim_code_completion"
    VISION = "vision"
    IMAGE_GENERATION = "image_generation"
    AUDIO = "audio"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    REALTIME_VOICE = "realtime_voice"
    VIDEO = "video"
    VIDEO_GENERATION = "video_generation"
    DOCUMENT_AI = "document_ai"
    OCR = "ocr"
    TOOL_USE = "tool_use"
    TOOL_SEARCH = "tool_search"
    COMPUTER_USE = "computer_use"
    CODE_EXECUTION = "code_execution"
    DEEP_RESEARCH = "deep_research"
    EMBEDDINGS = "embeddings"
    MULTIMODAL_EMBEDDINGS = "multimodal_embeddings"
    RERANKING = "reranking"
    MULTIMODAL_RETRIEVAL = "multimodal_retrieval"
    FORMAL_PROOF = "formal_proof"
    AGENTIC_WORKFLOW = "agentic_workflow"
    STRUCTURED_OUTPUT = "structured_output"
    LONG_CONTEXT = "long_context"
    CONTEXT_CACHING = "context_caching"
    CONTEXT_COMPACTION = "context_compaction"
    MULTIMODAL_SAFETY = "multimodal_safety"
    REALTIME_SOCIAL_INTELLIGENCE = "realtime_social_intelligence"
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
    context_window_tokens: int | None = None
    streaming: bool = False
    modalities: frozenset[str] = frozenset({"text"})
    languages: frozenset[str] = frozenset()
    free_tier: bool | None = None
    open_weight: bool | None = None
    metadata_source: str = "runtime_discovery"

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise ValueError("provider_id and model_id must not be empty")
        if not 0 <= self.cost_tier <= 5 or not 0 <= self.latency_tier <= 5:
            raise ValueError("cost_tier and latency_tier must be between 0 and 5")
        if self.context_window_tokens is not None and self.context_window_tokens < 1:
            raise ValueError("context_window_tokens must be positive when provided")
        if not self.modalities:
            raise ValueError("modalities must not be empty")


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
    min_context_window_tokens: int = 0
    require_streaming: bool = False
    require_free_tier: bool = False
    prefer_open_weight: bool = False

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if not 0 <= self.max_cost_tier <= 5:
            raise ValueError("max_cost_tier must be between 0 and 5")
        if self.min_context_window_tokens < 0:
            raise ValueError("min_context_window_tokens cannot be negative")


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
