from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from creator_app.model_fabric.capabilities import CapabilityEvidence, ModelCapability


class ProviderClass(StrEnum):
    CLOUD_API = "cloud_api"
    GATEWAY = "gateway"
    LOCAL_RUNTIME = "local_runtime"
    MODEL_VENDOR = "model_vendor"


@dataclass(frozen=True, slots=True)
class ProviderCapabilityProfile:
    """Discovery metadata only; it never proves that an adapter is connected."""

    provider_id: str
    display_name: str
    provider_class: ProviderClass
    model_families: tuple[str, ...]
    declared_capabilities: frozenset[ModelCapability]
    modalities: frozenset[str] = frozenset({"text"})
    evidence: CapabilityEvidence = CapabilityEvidence.DECLARED_ONLY
    catalogued_at: str = "2026-08-20"
    source_ref: str = "official-provider-docs-review-2026-08-20"
    production_evidence: bool = False

    def declares(self, required: frozenset[ModelCapability]) -> bool:
        return required.issubset(self.declared_capabilities)


C = ModelCapability


DEFAULT_PROVIDER_PROFILES: tuple[ProviderCapabilityProfile, ...] = (
    ProviderCapabilityProfile(
        provider_id="openai",
        display_name="OpenAI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("gpt", "o-series", "gpt-image", "realtime"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.CODE_REVIEW,
                C.COMPUTER_USE,
                C.DEEP_RESEARCH,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.IMAGE_GENERATION,
                C.SPEECH_TO_TEXT,
                C.TEXT_TO_SPEECH,
                C.REALTIME_VOICE,
                C.STRUCTURED_OUTPUT,
                C.MULTIMODAL_SAFETY,
                C.LONG_CONTEXT,
            }
        ),
        modalities=frozenset({"text", "image", "audio"}),
    ),
    ProviderCapabilityProfile(
        provider_id="anthropic",
        display_name="Anthropic",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("claude",),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.CODE_REVIEW,
                C.COMPUTER_USE,
                C.TOOL_SEARCH,
                C.CODE_EXECUTION,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.LONG_CONTEXT,
                C.CONTEXT_COMPACTION,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "image"}),
    ),
    ProviderCapabilityProfile(
        provider_id="google",
        display_name="Google AI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("gemini", "gemma"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.COMPUTER_USE,
                C.DEEP_RESEARCH,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.IMAGE_GENERATION,
                C.AUDIO_UNDERSTANDING,
                C.REALTIME_VOICE,
                C.VIDEO_UNDERSTANDING,
                C.TEXT_EMBEDDING,
                C.LONG_CONTEXT,
                C.CONTEXT_CACHING,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "video"}),
    ),
    ProviderCapabilityProfile(
        provider_id="xai",
        display_name="xAI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("grok", "imagine"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.IMAGE_GENERATION,
                C.VIDEO_GENERATION,
                C.REALTIME_VOICE,
                C.REALTIME_SOCIAL_INTELLIGENCE,
                C.LONG_CONTEXT,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "video"}),
    ),
    ProviderCapabilityProfile(
        provider_id="mistral",
        display_name="Mistral AI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("mistral", "codestral", "voxtral", "leanstral"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.CODE_REVIEW,
                C.FIM_CODE_COMPLETION,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.IMAGE_GENERATION,
                C.SPEECH_TO_TEXT,
                C.TEXT_TO_SPEECH,
                C.DOCUMENT_AI,
                C.OCR,
                C.FORMAL_PROOF,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "document"}),
    ),
    ProviderCapabilityProfile(
        provider_id="alibaba",
        display_name="Alibaba Cloud / Qwen",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("qwen", "qwen-coder", "qwen-omni"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.CODE_REVIEW,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.AUDIO_UNDERSTANDING,
                C.VIDEO_UNDERSTANDING,
                C.SPEECH_TO_TEXT,
                C.TEXT_TO_SPEECH,
                C.LONG_CONTEXT,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "video"}),
    ),
    ProviderCapabilityProfile(
        provider_id="deepseek",
        display_name="DeepSeek",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("deepseek", "deepseek-coder"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.CODE_REVIEW,
                C.FIM_CODE_COMPLETION,
                C.STRUCTURED_OUTPUT,
                C.LONG_CONTEXT,
            }
        ),
    ),
    ProviderCapabilityProfile(
        provider_id="aws_nova",
        display_name="Amazon Nova",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("nova", "nova-canvas", "nova-reel"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.IMAGE_UNDERSTANDING,
                C.VIDEO_UNDERSTANDING,
                C.IMAGE_GENERATION,
                C.VIDEO_GENERATION,
                C.MULTIMODAL_EMBEDDING,
                C.MULTIMODAL_RETRIEVAL,
                C.AGENTIC_WORKFLOW,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "video", "document"}),
    ),
    ProviderCapabilityProfile(
        provider_id="cohere",
        display_name="Cohere",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("command", "embed", "rerank"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.TEXT_EMBEDDING,
                C.MULTIMODAL_EMBEDDING,
                C.RERANKING,
                C.MULTIMODAL_RETRIEVAL,
                C.SPEECH_TO_TEXT,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "image", "audio", "document"}),
    ),
    ProviderCapabilityProfile(
        provider_id="nvidia",
        display_name="NVIDIA AI",
        provider_class=ProviderClass.MODEL_VENDOR,
        model_families=("nemotron", "nemotron-vl"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.IMAGE_UNDERSTANDING,
                C.VIDEO_UNDERSTANDING,
                C.MULTIMODAL_RETRIEVAL,
                C.LOCAL_MODEL_RUNTIME,
            }
        ),
        modalities=frozenset({"text", "image", "video"}),
    ),
    ProviderCapabilityProfile(
        provider_id="meta",
        display_name="Meta AI",
        provider_class=ProviderClass.MODEL_VENDOR,
        model_families=("llama",),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.IMAGE_UNDERSTANDING,
                C.LONG_CONTEXT,
                C.LOCAL_MODEL_RUNTIME,
            }
        ),
        modalities=frozenset({"text", "image"}),
    ),
    ProviderCapabilityProfile(
        provider_id="groq",
        display_name="Groq",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("hosted-open-models", "whisper"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.SPEECH_TO_TEXT,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "audio"}),
    ),
    ProviderCapabilityProfile(
        provider_id="moonshot",
        display_name="Moonshot AI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("kimi",),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.AGENTIC_WORKFLOW,
                C.LONG_CONTEXT,
            }
        ),
    ),
    ProviderCapabilityProfile(
        provider_id="zhipu",
        display_name="Zhipu AI",
        provider_class=ProviderClass.CLOUD_API,
        model_families=("glm", "glm-v"),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.CODE_GENERATION,
                C.AGENTIC_WORKFLOW,
                C.IMAGE_UNDERSTANDING,
                C.VIDEO_UNDERSTANDING,
                C.LONG_CONTEXT,
            }
        ),
        modalities=frozenset({"text", "image", "video"}),
    ),
    ProviderCapabilityProfile(
        provider_id="openrouter",
        display_name="OpenRouter",
        provider_class=ProviderClass.GATEWAY,
        model_families=("multi-provider-gateway",),
        declared_capabilities=frozenset(
            {
                C.REASONING,
                C.THINKING,
                C.CODE_GENERATION,
                C.IMAGE_UNDERSTANDING,
                C.LONG_CONTEXT,
                C.STRUCTURED_OUTPUT,
            }
        ),
        modalities=frozenset({"text", "image"}),
    ),
    ProviderCapabilityProfile(
        provider_id="ollama",
        display_name="Ollama",
        provider_class=ProviderClass.LOCAL_RUNTIME,
        model_families=("local-model-runtime",),
        declared_capabilities=frozenset({C.LOCAL_MODEL_RUNTIME}),
    ),
)


class ModelProviderCatalog:
    """Immutable catalog of discovered provider/model capability declarations."""

    def __init__(
        self,
        profiles: tuple[ProviderCapabilityProfile, ...] = DEFAULT_PROVIDER_PROFILES,
    ) -> None:
        ids = [profile.provider_id for profile in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("provider ids must be unique")
        self._profiles = profiles
        self._by_id = {profile.provider_id: profile for profile in profiles}

    def list(self) -> tuple[ProviderCapabilityProfile, ...]:
        return self._profiles

    def get(self, provider_id: str) -> ProviderCapabilityProfile | None:
        return self._by_id.get(provider_id)

    def discover(
        self,
        required: frozenset[ModelCapability],
        *,
        local_only: bool = False,
        allow_gateways: bool = True,
    ) -> tuple[ProviderCapabilityProfile, ...]:
        matches: list[ProviderCapabilityProfile] = []
        for profile in self._profiles:
            if local_only and profile.provider_class is not ProviderClass.LOCAL_RUNTIME:
                continue
            if not allow_gateways and profile.provider_class is ProviderClass.GATEWAY:
                continue
            if profile.declares(required):
                matches.append(profile)
        return tuple(matches)
