"""Deterministic semantic-to-prosody planner for AGNES Voice Persona."""

from __future__ import annotations

from creator_app.agnes.voice.contracts import (
    EmotionMode,
    ProsodyPlan,
    SemanticUtterance,
    SpeechContext,
    VoicePersona,
)


class VoicePersonaPlanner:
    """Plan delivery while keeping AGNES identity stable across situations."""

    def __init__(self, persona: VoicePersona | None = None) -> None:
        self.persona = persona or VoicePersona()

    def plan(self, utterance: SemanticUtterance, context: SpeechContext) -> ProsodyPlan:
        emotion = utterance.emotion_hint or self._emotion_from_context(utterance, context)
        rate = self._rate(emotion, context)
        pitch = self._pitch(emotion, context)
        energy = self._energy(emotion, context)
        before, after = self._pauses(utterance)
        emphasis = tuple(dict.fromkeys(utterance.key_phrases))
        instruction = self._style_instruction(emotion, context, emphasis)

        return ProsodyPlan(
            text=utterance.text,
            locale=context.locale,
            emotion=emotion,
            rate=rate,
            pitch=pitch,
            energy=energy,
            pause_before_ms=before,
            pause_after_ms=after,
            emphasis=emphasis,
            style_instruction=instruction,
        )

    def _emotion_from_context(
        self,
        utterance: SemanticUtterance,
        context: SpeechContext,
    ) -> EmotionMode:
        intent = utterance.intent.casefold()
        if context.urgency >= 0.75 or intent in {"alert", "warning", "incident"}:
            return EmotionMode.URGENT
        if context.sensitivity >= 0.7 or intent in {"comfort", "support", "apology"}:
            return EmotionMode.REASSURING
        if intent in {"teach", "explain", "guide", "onboarding"}:
            return EmotionMode.TEACHING
        if intent in {"decision", "security", "governance", "status-critical"}:
            return EmotionMode.SERIOUS
        if intent in {"celebrate", "success", "congratulate"}:
            return EmotionMode.CELEBRATORY
        if context.familiarity >= 0.7:
            return EmotionMode.WARM
        return EmotionMode.NEUTRAL

    def _rate(self, emotion: EmotionMode, context: SpeechContext) -> float:
        base = {
            EmotionMode.NEUTRAL: 1.00,
            EmotionMode.WARM: 0.98,
            EmotionMode.SERIOUS: 0.93,
            EmotionMode.TEACHING: 0.91,
            EmotionMode.REASSURING: 0.88,
            EmotionMode.URGENT: 1.10,
            EmotionMode.CELEBRATORY: 1.04,
        }[emotion]
        if context.audience_role.casefold() in {"executive", "auditor", "operator"}:
            base -= 0.03
        return round(min(1.18, max(0.82, base)), 2)

    def _pitch(self, emotion: EmotionMode, context: SpeechContext) -> float:
        base = {
            EmotionMode.NEUTRAL: 0.00,
            EmotionMode.WARM: 0.08,
            EmotionMode.SERIOUS: -0.08,
            EmotionMode.TEACHING: 0.02,
            EmotionMode.REASSURING: -0.02,
            EmotionMode.URGENT: 0.05,
            EmotionMode.CELEBRATORY: 0.12,
        }[emotion]
        if context.sensitivity >= 0.8:
            base -= 0.03
        return round(min(0.2, max(-0.2, base)), 2)

    def _energy(self, emotion: EmotionMode, context: SpeechContext) -> float:
        base = {
            EmotionMode.NEUTRAL: 0.50,
            EmotionMode.WARM: 0.56,
            EmotionMode.SERIOUS: 0.52,
            EmotionMode.TEACHING: 0.50,
            EmotionMode.REASSURING: 0.42,
            EmotionMode.URGENT: 0.72,
            EmotionMode.CELEBRATORY: 0.70,
        }[emotion]
        base *= 0.8 + (self.persona.expressiveness * 0.4)
        return round(min(0.85, max(0.30, base)), 2)

    @staticmethod
    def _pauses(utterance: SemanticUtterance) -> tuple[int, int]:
        before = int(80 + (utterance.importance * 220))
        after = int(100 + (utterance.importance * 260))
        return before, after

    def _style_instruction(
        self,
        emotion: EmotionMode,
        context: SpeechContext,
        emphasis: tuple[str, ...],
    ) -> str:
        audience = context.audience_role.strip() or "user"
        emphasis_text = ", ".join(emphasis) if emphasis else "none"
        thai_rule = (
            "Preserve Thai lexical tones and word identity; use prosody, pacing, "
            "energy, and pauses for expression. "
            if context.locale.lower().startswith("th")
            else "Preserve lexical pronunciation and word identity. "
        )
        return (
            f"Speak as {self.persona.name} with a stable, recognizable persona. "
            f"Delivery mode: {emotion.value}. Audience: {audience}. "
            f"Warmth={self.persona.warmth:.2f}; authority={self.persona.authority:.2f}. "
            f"Emphasize semantically important phrases: {emphasis_text}. "
            f"{thai_rule}Do not read stage directions aloud."
        )
