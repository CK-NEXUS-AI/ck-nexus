"""Provider-neutral multimodal creation and transformation contracts for AGNES.

These contracts describe capabilities only. They do not authenticate providers,
perform external calls, or grant mutation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaType(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class MediaOperation(StrEnum):
    GENERATE = "generate"
    TRANSFORM = "transform"
    INPAINT = "inpaint"
    OUTPAINT = "outpaint"
    REMOVE_BACKGROUND = "remove_background"
    REPLACE_BACKGROUND = "replace_background"
    REMOVE_OBJECT = "remove_object"
    REMOVE_TEXT = "remove_text"
    UPSCALE = "upscale"
    IMAGE_TO_PROMPT = "image_to_prompt"
    TEXT_TO_SPEECH = "text_to_speech"
    SPEECH_TO_TEXT = "speech_to_text"
    VOICE_CLONE = "voice_clone"
    AUDIO_ENHANCE = "audio_enhance"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    AVATAR_VIDEO = "avatar_video"
    TRANSCRIBE = "transcribe"
    SUBTITLE = "subtitle"
    TRANSLATE = "translate"


@dataclass(frozen=True, slots=True)
class MediaCapability:
    capability_id: str
    media_type: MediaType
    operation: MediaOperation
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    provider_id: str | None = None
    model_id: str | None = None
    quality_tier: int = 1
    latency_tier: int = 1
    cost_tier: int = 1
    requires_network: bool = True
    requires_consent: bool = False
    verification_required: bool = True

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("capability_id must not be empty")
        for name, value in (
            ("quality_tier", self.quality_tier),
            ("latency_tier", self.latency_tier),
            ("cost_tier", self.cost_tier),
        ):
            if not 0 <= value <= 5:
                raise ValueError(f"{name} must be between 0 and 5")
        if not self.input_types or not self.output_types:
            raise ValueError("input_types and output_types must not be empty")


@dataclass(frozen=True, slots=True)
class MediaRequest:
    capability_id: str
    prompt: str = ""
    source_asset_ids: tuple[str, ...] = ()
    target_language: str | None = None
    consent_receipt_id: str | None = None


@dataclass(frozen=True, slots=True)
class MediaResult:
    capability_id: str
    asset_ids: tuple[str, ...]
    provider_id: str
    model_id: str
    evidence_digest: str
    verified: bool
