"""Low-risk, transient communication-tone estimation.

This module intentionally avoids diagnosis and sensitive-attribute inference. Its
output is a short-lived conversation hint, not a durable user trait.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToneEstimate:
    label: str
    confidence: float
    evidence_terms: tuple[str, ...]
    persistent: bool = False
    diagnostic: bool = False


_POSITIVE = ("ดีมาก", "เยี่ยม", "ขอบคุณ", "happy", "great", "excellent")
_CONCERNED = ("กังวล", "เครียด", "เหนื่อย", "ไม่ไหว", "worried", "stressed", "tired")
_URGENT = ("ด่วน", "ทันที", "เร็ว", "urgent", "asap")


def estimate_tone(text: str) -> ToneEstimate:
    """Return a conservative, non-diagnostic tone hint from the current message."""
    lowered = text.casefold()
    matched_concern = tuple(term for term in _CONCERNED if term in lowered)
    matched_urgent = tuple(term for term in _URGENT if term in lowered)
    matched_positive = tuple(term for term in _POSITIVE if term in lowered)

    if matched_concern:
        confidence = min(0.65, 0.45 + 0.05 * len(matched_concern))
        return ToneEstimate("concerned", confidence, matched_concern)
    if matched_urgent:
        confidence = min(0.65, 0.45 + 0.05 * len(matched_urgent))
        return ToneEstimate("urgent", confidence, matched_urgent)
    if matched_positive:
        confidence = min(0.65, 0.45 + 0.05 * len(matched_positive))
        return ToneEstimate("positive", confidence, matched_positive)
    return ToneEstimate("neutral", 0.35, ())
