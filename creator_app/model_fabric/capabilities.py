from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ModelCapability(StrEnum):
    """Provider-neutral model capabilities used for discovery and routing policy."""

    REASONING = "reasoning"
    THINKING = "thinking"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    FIM_CODE_COMPLETION = "fim_code_completion"
    COMPUTER_USE = "computer_use"
    DEEP_RESEARCH = "deep_research"
    TOOL_SEARCH = "tool_search"
    AGENTIC_WORKFLOW = "agentic_workflow"
    CODE_EXECUTION = "code_execution"
    FORMAL_PROOF = "formal_proof"
    IMAGE_UNDERSTANDING = "image_understanding"
    IMAGE_GENERATION = "image_generation"
    AUDIO_UNDERSTANDING = "audio_understanding"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    REALTIME_VOICE = "realtime_voice"
    VIDEO_UNDERSTANDING = "video_understanding"
    VIDEO_GENERATION = "video_generation"
    DOCUMENT_AI = "document_ai"
    OCR = "ocr"
    TEXT_EMBEDDING = "text_embedding"
    MULTIMODAL_EMBEDDING = "multimodal_embedding"
    RERANKING = "reranking"
    MULTIMODAL_RETRIEVAL = "multimodal_retrieval"
    LONG_CONTEXT = "long_context"
    CONTEXT_CACHING = "context_caching"
    CONTEXT_COMPACTION = "context_compaction"
    STRUCTURED_OUTPUT = "structured_output"
    MULTIMODAL_SAFETY = "multimodal_safety"
    REALTIME_SOCIAL_INTELLIGENCE = "realtime_social_intelligence"
    LOCAL_MODEL_RUNTIME = "local_model_runtime"


class CapabilityEvidence(StrEnum):
    """Evidence level for a catalog declaration.

    Catalog declarations are never production evidence. The enum exists so a
    future verified runtime manifest can supersede declarations explicitly.
    """

    DECLARED_ONLY = "declared_only"
    VERIFIED_CODE = "verified_code"
    VERIFIED_TEST = "verified_test"
    VERIFIED_RUNTIME = "verified_runtime"


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    required: frozenset[ModelCapability]
    local_only: bool = False
    allow_gateways: bool = True

    @classmethod
    def of(
        cls,
        *capabilities: ModelCapability,
        local_only: bool = False,
        allow_gateways: bool = True,
    ) -> CapabilityRequirement:
        return cls(
            required=frozenset(capabilities),
            local_only=local_only,
            allow_gateways=allow_gateways,
        )
