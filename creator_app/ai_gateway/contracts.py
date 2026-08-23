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
    VIDEO = "video"
    AUDIO = "audio"
    TOOL_USE = "tool_use"
    EMBEDDINGS = "embeddings"
    LOCAL = "local"
    LONG_CONTEXT = "long_context"
    THINKING_CONTROL = "thinking_control"
    THINKING_CONTINUITY = "thinking_continuity"
    AGENTIC_EXECUTION = "agentic_execution"
    ENVIRONMENT_FEEDBACK = "environment_feedback"
    LOCAL_MULTIMODAL = "local_multimodal"
    QUANTIZED_RUNTIME = "quantized_runtime"
    RED_TEAM_MODEL = "red_team_model"
    MODEL_ATTESTATION = "model_attestation"


class DataClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"


class ModelRiskClass(StrEnum):
    STANDARD = "standard"
    EXPERIMENTAL = "experimental"
    RED_TEAM_ONLY = "red_team_only"
    SAFETY_MODIFIED = "safety_modified"
    UNTRUSTED_WEIGHTS = "untrusted_weights"


class AttestationState(StrEnum):
    CLAIMED = "claimed"
    MEASURED = "measured"
    VERIFIED = "verified"


class ReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    ADAPTIVE = "adaptive"


class ModelUseLane(StrEnum):
    DEVELOPMENT = "development"
    EVALUATION = "evaluation"
    RED_TEAM = "red_team"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class GenerationProfile:
    temperature: float | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    max_tokens: int | None = None
    reasoning_effort: ReasoningEffort | None = None
    preserve_reasoning_context: bool = False

    def __post_init__(self) -> None:
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature must not be negative")
        if self.top_p is not None and not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
        if self.repetition_penalty is not None and self.repetition_penalty <= 0:
            raise ValueError("repetition_penalty must be positive")


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    model_repo: str = ""
    revision_sha: str = ""
    weight_digest: str = ""
    base_model: str = ""
    modifier: str = ""
    quantization: str = ""
    license_id: str = ""
    attestation: AttestationState = AttestationState.CLAIMED


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    provider_id: str
    model_id: str
    capabilities: frozenset[ModelCapability]
    cost_tier: int = 1
    latency_tier: int = 1
    local: bool = False
    runtime_id: str = "remote"
    risk_class: ModelRiskClass = ModelRiskClass.STANDARD
    context_window_tokens: int | None = None
    generation_profile: GenerationProfile = GenerationProfile()
    provenance: ModelProvenance = ModelProvenance()

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise ValueError("provider_id and model_id must not be empty")
        if not self.runtime_id.strip():
            raise ValueError("runtime_id must not be empty")
        if not 0 <= self.cost_tier <= 5 or not 0 <= self.latency_tier <= 5:
            raise ValueError("cost_tier and latency_tier must be between 0 and 5")
        if self.context_window_tokens is not None and self.context_window_tokens <= 0:
            raise ValueError("context_window_tokens must be positive")


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
    model_use_lane: ModelUseLane = ModelUseLane.DEVELOPMENT

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
