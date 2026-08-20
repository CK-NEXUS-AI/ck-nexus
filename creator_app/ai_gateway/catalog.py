"""Declared global provider capability catalog for CK-NEXUS.

Declarations are discovery metadata only. They do not prove that a provider is
connected, configured, healthy, authorized, executable, or production verified.
Runtime adapters remain the authority for live model discovery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import ModelCapability


class ProviderClass(StrEnum):
    CLOUD_API = "cloud_api"
    GATEWAY = "gateway"
    MODEL_VENDOR = "model_vendor"
    LOCAL_RUNTIME = "local_runtime"


@dataclass(frozen=True, slots=True)
class ProviderCapabilityDeclaration:
    provider_id: str
    display_name: str
    provider_class: ProviderClass
    model_families: tuple[str, ...]
    capabilities: frozenset[ModelCapability]
    modalities: frozenset[str] = frozenset({"text"})
    source_ref: str = "official-provider-docs-review"
    reviewed_at: str = "2026-08-20"
    classification: str = "DECLARED_ONLY"
    production_evidence: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.display_name.strip():
            raise ValueError("provider_id and display_name must not be empty")
        if not self.capabilities:
            raise ValueError("capabilities must not be empty")
        if not self.modalities:
            raise ValueError("modalities must not be empty")

    def supports(self, required: frozenset[ModelCapability]) -> bool:
        return required.issubset(self.capabilities)


C = ModelCapability


def _decl(
    provider_id: str,
    display_name: str,
    provider_class: ProviderClass,
    model_families: tuple[str, ...],
    capabilities: tuple[ModelCapability, ...],
    *,
    modalities: tuple[str, ...] = ("text",),
    source_ref: str,
) -> ProviderCapabilityDeclaration:
    return ProviderCapabilityDeclaration(
        provider_id=provider_id,
        display_name=display_name,
        provider_class=provider_class,
        model_families=model_families,
        capabilities=frozenset(capabilities),
        modalities=frozenset(modalities),
        source_ref=source_ref,
    )


DEFAULT_DECLARATIONS: tuple[ProviderCapabilityDeclaration, ...] = (
    _decl(
        "openai",
        "OpenAI",
        ProviderClass.CLOUD_API,
        ("gpt", "o-series", "gpt-image", "realtime"),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.CODE_REVIEW,
            C.COMPUTER_USE,
            C.DEEP_RESEARCH,
            C.AGENTIC_WORKFLOW,
            C.VISION,
            C.IMAGE_GENERATION,
            C.SPEECH_TO_TEXT,
            C.TEXT_TO_SPEECH,
            C.REALTIME_VOICE,
            C.STRUCTURED_OUTPUT,
            C.LONG_CONTEXT,
            C.MULTIMODAL_SAFETY,
        ),
        modalities=("text", "image", "audio"),
        source_ref="official-docs:openai",
    ),
    _decl(
        "anthropic",
        "Anthropic",
        ProviderClass.CLOUD_API,
        ("claude",),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.CODE_REVIEW,
            C.VISION,
            C.COMPUTER_USE,
            C.TOOL_USE,
            C.TOOL_SEARCH,
            C.CODE_EXECUTION,
            C.AGENTIC_WORKFLOW,
            C.LONG_CONTEXT,
            C.CONTEXT_COMPACTION,
            C.STRUCTURED_OUTPUT,
        ),
        modalities=("text", "image"),
        source_ref="official-docs:anthropic",
    ),
    _decl(
        "gemini",
        "Google Gemini",
        ProviderClass.CLOUD_API,
        ("gemini", "gemma"),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.VISION,
            C.AUDIO,
            C.VIDEO,
            C.COMPUTER_USE,
            C.DEEP_RESEARCH,
            C.AGENTIC_WORKFLOW,
            C.IMAGE_GENERATION,
            C.REALTIME_VOICE,
            C.EMBEDDINGS,
            C.LONG_CONTEXT,
            C.CONTEXT_CACHING,
            C.STRUCTURED_OUTPUT,
        ),
        modalities=("text", "image", "audio", "video"),
        source_ref="official-docs:google-ai",
    ),
    _decl(
        "xai",
        "xAI",
        ProviderClass.CLOUD_API,
        ("grok", "imagine"),
        (
            C.TEXT,
            C.REASONING,
            C.CODE,
            C.VISION,
            C.IMAGE_GENERATION,
            C.VIDEO_GENERATION,
            C.REALTIME_VOICE,
            C.REALTIME_SOCIAL_INTELLIGENCE,
            C.LONG_CONTEXT,
        ),
        modalities=("text", "image", "audio", "video"),
        source_ref="official-docs:xai",
    ),
    _decl(
        "mistral",
        "Mistral AI",
        ProviderClass.CLOUD_API,
        ("mistral", "codestral", "voxtral", "leanstral"),
        (
            C.TEXT,
            C.REASONING,
            C.CODE,
            C.CODE_REVIEW,
            C.FIM_CODE_COMPLETION,
            C.VISION,
            C.IMAGE_GENERATION,
            C.SPEECH_TO_TEXT,
            C.TEXT_TO_SPEECH,
            C.DOCUMENT_AI,
            C.OCR,
            C.FORMAL_PROOF,
            C.AGENTIC_WORKFLOW,
            C.STRUCTURED_OUTPUT,
        ),
        modalities=("text", "image", "audio", "document"),
        source_ref="official-docs:mistral",
    ),
    _decl(
        "alibaba",
        "Alibaba Cloud / Qwen",
        ProviderClass.CLOUD_API,
        ("qwen", "qwen-coder", "qwen-omni"),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.CODE_REVIEW,
            C.VISION,
            C.AUDIO,
            C.VIDEO,
            C.SPEECH_TO_TEXT,
            C.TEXT_TO_SPEECH,
            C.AGENTIC_WORKFLOW,
            C.LONG_CONTEXT,
        ),
        modalities=("text", "image", "audio", "video"),
        source_ref="official-docs:alibaba-qwen",
    ),
    _decl(
        "deepseek",
        "DeepSeek",
        ProviderClass.CLOUD_API,
        ("deepseek", "deepseek-coder"),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.CODE_REVIEW,
            C.FIM_CODE_COMPLETION,
            C.STRUCTURED_OUTPUT,
            C.LONG_CONTEXT,
        ),
        source_ref="official-docs:deepseek",
    ),
    _decl(
        "aws_nova",
        "Amazon Nova",
        ProviderClass.CLOUD_API,
        ("nova", "nova-canvas", "nova-reel"),
        (
            C.TEXT,
            C.REASONING,
            C.VISION,
            C.VIDEO,
            C.IMAGE_GENERATION,
            C.VIDEO_GENERATION,
            C.MULTIMODAL_EMBEDDINGS,
            C.MULTIMODAL_RETRIEVAL,
            C.AGENTIC_WORKFLOW,
        ),
        modalities=("text", "image", "audio", "video", "document"),
        source_ref="official-docs:amazon-nova",
    ),
    _decl(
        "cohere",
        "Cohere",
        ProviderClass.CLOUD_API,
        ("command", "embed", "rerank"),
        (
            C.TEXT,
            C.REASONING,
            C.EMBEDDINGS,
            C.MULTIMODAL_EMBEDDINGS,
            C.RERANKING,
            C.MULTIMODAL_RETRIEVAL,
            C.SPEECH_TO_TEXT,
            C.STRUCTURED_OUTPUT,
        ),
        modalities=("text", "image", "audio", "document"),
        source_ref="official-docs:cohere",
    ),
    _decl(
        "nvidia",
        "NVIDIA AI",
        ProviderClass.MODEL_VENDOR,
        ("nemotron", "nemotron-vl"),
        (
            C.TEXT,
            C.REASONING,
            C.CODE,
            C.VISION,
            C.VIDEO,
            C.MULTIMODAL_RETRIEVAL,
            C.LOCAL,
        ),
        modalities=("text", "image", "video"),
        source_ref="official-docs:nvidia-nemotron",
    ),
    _decl(
        "meta",
        "Meta AI",
        ProviderClass.MODEL_VENDOR,
        ("llama",),
        (C.TEXT, C.REASONING, C.CODE, C.VISION, C.LONG_CONTEXT, C.LOCAL),
        modalities=("text", "image"),
        source_ref="official-docs:meta-llama",
    ),
    _decl(
        "groq",
        "Groq",
        ProviderClass.CLOUD_API,
        ("hosted-open-models", "whisper"),
        (C.TEXT, C.REASONING, C.CODE, C.SPEECH_TO_TEXT, C.STRUCTURED_OUTPUT),
        modalities=("text", "audio"),
        source_ref="official-docs:groq",
    ),
    _decl(
        "moonshot",
        "Moonshot AI",
        ProviderClass.CLOUD_API,
        ("kimi",),
        (C.TEXT, C.REASONING, C.THINKING, C.CODE, C.AGENTIC_WORKFLOW, C.LONG_CONTEXT),
        source_ref="official-docs:moonshot",
    ),
    _decl(
        "zhipu",
        "Zhipu AI",
        ProviderClass.CLOUD_API,
        ("glm", "glm-v"),
        (
            C.TEXT,
            C.REASONING,
            C.CODE,
            C.VISION,
            C.VIDEO,
            C.AGENTIC_WORKFLOW,
            C.LONG_CONTEXT,
        ),
        modalities=("text", "image", "video"),
        source_ref="official-docs:zhipu",
    ),
    _decl(
        "openrouter",
        "OpenRouter",
        ProviderClass.GATEWAY,
        ("multi-provider-gateway",),
        (
            C.TEXT,
            C.REASONING,
            C.THINKING,
            C.CODE,
            C.VISION,
            C.LONG_CONTEXT,
            C.STRUCTURED_OUTPUT,
        ),
        modalities=("text", "image"),
        source_ref="official-docs:openrouter",
    ),
    _decl(
        "ollama",
        "Ollama",
        ProviderClass.LOCAL_RUNTIME,
        ("local-model-runtime",),
        (C.TEXT, C.LOCAL),
        source_ref="official-docs:ollama",
    ),
)


class GlobalCapabilityCatalog:
    """Immutable provider declaration catalog used for discovery, never execution."""

    def __init__(
        self,
        declarations: tuple[ProviderCapabilityDeclaration, ...] = DEFAULT_DECLARATIONS,
    ) -> None:
        ids = [item.provider_id for item in declarations]
        if len(ids) != len(set(ids)):
            raise ValueError("provider ids must be unique")
        self._declarations = declarations
        self._by_id = {item.provider_id: item for item in declarations}

    def list(self) -> tuple[ProviderCapabilityDeclaration, ...]:
        return self._declarations

    def get(self, provider_id: str) -> ProviderCapabilityDeclaration | None:
        return self._by_id.get(provider_id)

    def discover(
        self,
        required: frozenset[ModelCapability],
        *,
        local_only: bool = False,
        include_gateways: bool = True,
    ) -> tuple[ProviderCapabilityDeclaration, ...]:
        matches: list[ProviderCapabilityDeclaration] = []
        for item in self._declarations:
            if local_only and item.provider_class is not ProviderClass.LOCAL_RUNTIME:
                continue
            if not include_gateways and item.provider_class is ProviderClass.GATEWAY:
                continue
            if item.supports(required):
                matches.append(item)
        return tuple(matches)
