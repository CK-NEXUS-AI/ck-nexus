"""Provider-neutral semantic IR for AGNES Voice Persona.

The IR carries meaning, audience context and intended delivery separately from
provider-specific TTS controls. It never rewrites lexical content merely to
force emotion or prosody.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json


class EmotionMode(StrEnum):
    NEUTRAL = "neutral"
    WARM = "warm"
    SERIOUS = "serious"
    TEACHING = "teaching"
    REASSURING = "reassuring"
    URGENT = "urgent"
    CELEBRATORY = "celebratory"


@dataclass(frozen=True, slots=True)
class VoicePersona:
    """Stable identity parameters that should not drift between turns."""

    persona_id: str = "agnes.default.v1"
    name: str = "AGNES"
    warmth: float = 0.68
    authority: float = 0.62
    expressiveness: float = 0.55
    consistency: float = 0.82

    def __post_init__(self) -> None:
        for name in ("warmth", "authority", "expressiveness", "consistency"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class SpeechContext:
    """Who AGNES is speaking to and the situational constraints."""

    audience_role: str = "user"
    familiarity: float = 0.5
    urgency: float = 0.0
    sensitivity: float = 0.0
    locale: str = "th-TH"

    def __post_init__(self) -> None:
        for name in ("familiarity", "urgency", "sensitivity"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if not self.locale.strip():
            raise ValueError("locale must not be empty")


@dataclass(frozen=True, slots=True)
class SemanticUtterance:
    """Meaning-bearing input to the voice planner."""

    text: str
    intent: str
    importance: float = 0.5
    emotion_hint: EmotionMode | None = None
    key_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.intent.strip():
            raise ValueError("intent must not be empty")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance must be between 0 and 1")
        for phrase in self.key_phrases:
            if phrase and phrase not in self.text:
                raise ValueError("every key phrase must occur in text")


@dataclass(frozen=True, slots=True)
class ProsodyPlan:
    """Deterministic delivery plan before provider-specific rendering."""

    text: str
    locale: str
    emotion: EmotionMode
    rate: float
    pitch: float
    energy: float
    pause_before_ms: int
    pause_after_ms: int
    emphasis: tuple[str, ...]
    style_instruction: str
    lexical_form_preserved: bool = True
    thai_lexical_tone_preserved: bool = True
    ir_version: str = "agnes.voice.semantic-ir.v1"

    def __post_init__(self) -> None:
        if not 0.7 <= self.rate <= 1.3:
            raise ValueError("rate must be between 0.7 and 1.3")
        if not -1.0 <= self.pitch <= 1.0:
            raise ValueError("pitch must be between -1 and 1")
        if not 0.0 <= self.energy <= 1.0:
            raise ValueError("energy must be between 0 and 1")
        if self.pause_before_ms < 0 or self.pause_after_ms < 0:
            raise ValueError("pause values must be non-negative")
        if not self.lexical_form_preserved:
            raise ValueError("voice planning may not mutate lexical content")
        if self.locale.lower().startswith("th") and not self.thai_lexical_tone_preserved:
            raise ValueError("Thai lexical tones must be preserved")

    def to_semantic_ir(self) -> dict[str, object]:
        """Return a serializable provider-neutral representation."""
        payload = asdict(self)
        payload["emotion"] = self.emotion.value
        return payload

    def digest(self) -> str:
        """Stable digest used by verification/evidence layers."""
        encoded = json.dumps(
            self.to_semantic_ir(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
