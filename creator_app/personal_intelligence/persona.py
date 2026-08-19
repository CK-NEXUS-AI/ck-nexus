"""Natural communication policy that remains transparent about AI identity."""

from __future__ import annotations

from dataclasses import dataclass

from .tone import ToneEstimate


@dataclass(frozen=True, slots=True)
class PersonaPreferences:
    language: str = "th"
    brevity: str = "balanced"
    warmth: str = "warm"
    humor: str = "light"


@dataclass(frozen=True, slots=True)
class ResponseStyle:
    language: str
    brevity: str
    warmth: str
    humor: str
    tone_hint: str
    transparent_ai: bool = True
    claim_real_emotions: bool = False
    imitate_human_identity: bool = False


def choose_response_style(
    preferences: PersonaPreferences,
    tone: ToneEstimate,
) -> ResponseStyle:
    """Adapt presentation without pretending the system is a human being."""
    warmth = preferences.warmth
    humor = preferences.humor
    if tone.label == "concerned":
        warmth = "supportive"
        humor = "none"
    elif tone.label == "urgent":
        warmth = "direct"
        humor = "none"
    return ResponseStyle(
        language=preferences.language,
        brevity=preferences.brevity,
        warmth=warmth,
        humor=humor,
        tone_hint=tone.label,
    )
