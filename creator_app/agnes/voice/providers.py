"""Provider payload adapters for AGNES Voice Persona.

These adapters only translate verified semantic/prosody plans into provider
request payloads. They do not own persona policy or semantic decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from creator_app.agnes.voice.contracts import EmotionMode, ProsodyPlan


@dataclass(frozen=True, slots=True)
class OpenAIVoiceAdapter:
    model: str = "gpt-4o-mini-tts"
    voice: str = "marin"

    def build_request(self, plan: ProsodyPlan) -> dict[str, object]:
        """Build an OpenAI Speech API request without credentials."""
        instructions = (
            f"{plan.style_instruction} "
            f"Target speaking rate approximately {plan.rate:.2f}x. "
            f"Use natural pauses around important ideas; intended emotion: {plan.emotion.value}."
        )
        return {
            "model": self.model,
            "voice": self.voice,
            "input": plan.text,
            "instructions": instructions,
            "speed": plan.rate,
            "response_format": "wav",
        }


@dataclass(frozen=True, slots=True)
class ElevenLabsVoiceAdapter:
    model_id: str = "eleven_multilingual_v2"
    stability_floor: float = 0.35
    similarity_boost: float = 0.75

    def build_request(self, plan: ProsodyPlan) -> dict[str, object]:
        """Build an ElevenLabs synthesis payload without credentials."""
        stability = self._stability(plan.emotion)
        style = self._style(plan.emotion)
        return {
            "text": plan.text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": self.similarity_boost,
                "style": style,
                "use_speaker_boost": True,
                "speed": min(1.2, max(0.7, plan.rate)),
            },
        }

    def _stability(self, emotion: EmotionMode) -> float:
        raw = {
            EmotionMode.NEUTRAL: 0.65,
            EmotionMode.WARM: 0.52,
            EmotionMode.SERIOUS: 0.72,
            EmotionMode.TEACHING: 0.67,
            EmotionMode.REASSURING: 0.60,
            EmotionMode.URGENT: 0.50,
            EmotionMode.CELEBRATORY: 0.45,
        }[emotion]
        return round(max(self.stability_floor, raw), 2)

    @staticmethod
    def _style(emotion: EmotionMode) -> float:
        # Conservative by design: style exaggeration can reduce stability.
        return {
            EmotionMode.NEUTRAL: 0.00,
            EmotionMode.WARM: 0.05,
            EmotionMode.SERIOUS: 0.00,
            EmotionMode.TEACHING: 0.02,
            EmotionMode.REASSURING: 0.03,
            EmotionMode.URGENT: 0.05,
            EmotionMode.CELEBRATORY: 0.08,
        }[emotion]
