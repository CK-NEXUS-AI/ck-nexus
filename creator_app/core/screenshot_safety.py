from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ScreenshotRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class ScreenshotSignal(BaseModel):
    signal_id: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    details: str = ""


class ScreenshotAssessment(BaseModel):
    subject: str
    risk: ScreenshotRisk
    signals: list[ScreenshotSignal] = Field(default_factory=list)
    requires_human_approval: bool = True
    execution_allowed: bool = False


class ScreenshotSafetyGate:
    """Fail-closed gate for screenshot-derived computer-use actions."""

    def assess(
        self,
        *,
        subject: str,
        signals: list[ScreenshotSignal],
        policy_allows: bool,
    ) -> ScreenshotAssessment:
        if not signals:
            return ScreenshotAssessment(subject=subject, risk=ScreenshotRisk.BLOCKED)

        max_confidence = max(signal.confidence for signal in signals)
        risky = any("prompt-injection" in signal.source.lower() for signal in signals)
        if risky and max_confidence >= 0.5:
            risk = ScreenshotRisk.HIGH
        elif max_confidence >= 0.8:
            risk = ScreenshotRisk.MEDIUM
        else:
            risk = ScreenshotRisk.LOW

        requires_approval = risk in {ScreenshotRisk.MEDIUM, ScreenshotRisk.HIGH}
        execution_allowed = policy_allows and risk == ScreenshotRisk.LOW
        return ScreenshotAssessment(
            subject=subject,
            risk=risk,
            signals=list(signals),
            requires_human_approval=requires_approval,
            execution_allowed=execution_allowed,
        )
