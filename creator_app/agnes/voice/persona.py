from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VoiceMode(StrEnum):
    DEFAULT = "default"
    FORMAL = "formal"
    EXPLANATORY = "explanatory"
    WARNING = "warning"
    SUPPORTIVE = "supportive"


@dataclass(frozen=True)
class VoiceContext:
    mode: VoiceMode = VoiceMode.DEFAULT
    locale: str = "th-TH"
    user_relationship: str = "neutral"
    importance: float = 0.5
    complexity: float = 0.5
    noisy_environment: bool = False


@dataclass(frozen=True)
class VoiceProfile:
    pitch_semitones: float
    rate: float
    volume_db: float
    pause_ms: int
    emotion: str
    style: str
    breath_every_sentences: int
    text_source_of_truth: bool = True


_BASE = {
    VoiceMode.DEFAULT: VoiceProfile(0.0, 1.00, 0.0, 200, "neutral_friendly", "conversational", 4),
    VoiceMode.FORMAL: VoiceProfile(-2.0, 0.95, 1.0, 250, "serious", "formal", 4),
    VoiceMode.EXPLANATORY: VoiceProfile(1.0, 0.85, 0.0, 400, "gentle", "explanatory", 4),
    VoiceMode.WARNING: VoiceProfile(-3.0, 0.90, 3.0, 500, "alert", "warning", 3),
    VoiceMode.SUPPORTIVE: VoiceProfile(3.0, 1.05, 2.0, 250, "encouraging", "supportive", 4),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def resolve_voice_profile(context: VoiceContext) -> VoiceProfile:
    """Resolve persona controls without invoking a TTS provider.

    The resolver preserves a stable persona while allowing bounded contextual
    adaptation. Provider-specific controls are applied later by an adapter.
    """
    base = _BASE[context.mode]
    rate = base.rate
    pause_ms = base.pause_ms

    if context.complexity >= 0.75:
        rate -= 0.08
        pause_ms += 100
    if context.importance >= 0.80:
        rate -= 0.04
        pause_ms += 100
    if context.noisy_environment:
        # Prefer text in orchestration policy; if voice is still requested,
        # keep delivery slower and clearer rather than louder by default.
        rate -= 0.05
        pause_ms += 50

    return VoiceProfile(
        pitch_semitones=_clamp(base.pitch_semitones, -6.0, 6.0),
        rate=_clamp(rate, 0.7, 1.3),
        volume_db=_clamp(base.volume_db, -6.0, 6.0),
        pause_ms=int(_clamp(float(pause_ms), 50.0, 800.0)),
        emotion=base.emotion,
        style=base.style,
        breath_every_sentences=base.breath_every_sentences,
    )
