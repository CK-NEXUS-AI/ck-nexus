"""Response planning that separates cognitive result from presentation style."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from creator_app.personal_intelligence import (
    PersonaPreferences,
    ResponseStyle,
    choose_response_style,
    estimate_tone,
)


@dataclass(frozen=True, slots=True)
class ConversationPlan:
    language: str
    brevity: str
    warmth: str
    humor: str
    tone_hint: str
    uncertainty_behavior: str
    transparent_ai: bool
    claim_real_emotions: bool
    imitate_human_identity: bool
    plan_digest: str


def plan_response(
    user_message: str,
    *,
    preferences: PersonaPreferences | None = None,
    confidence: float = 1.0,
) -> ConversationPlan:
    """Create a stable presentation plan without pretending to be human."""
    if not user_message.strip():
        raise ValueError("user_message must not be empty")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    prefs = preferences or PersonaPreferences()
    tone = estimate_tone(user_message)
    style: ResponseStyle = choose_response_style(prefs, tone)
    uncertainty = "state_uncertainty_and_ask_or_verify" if confidence < 0.6 else "answer_normally"
    payload = {
        **asdict(style),
        "uncertainty_behavior": uncertainty,
        "authority": "CK-NEXUS",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return ConversationPlan(
        language=style.language,
        brevity=style.brevity,
        warmth=style.warmth,
        humor=style.humor,
        tone_hint=style.tone_hint,
        uncertainty_behavior=uncertainty,
        transparent_ai=style.transparent_ai,
        claim_real_emotions=style.claim_real_emotions,
        imitate_human_identity=style.imitate_human_identity,
        plan_digest=hashlib.sha256(encoded).hexdigest(),
    )
