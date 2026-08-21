from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class FeedbackSignal(StrEnum):
    CONTINUE = "continue"
    CORRECT = "correct"
    REPLAN = "replan"
    ASK_HUMAN = "ask_human"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class FeedbackObservation:
    goal_metric: float
    observed_metric: float
    tolerance: float
    risk: str = "low"
    observed_at: datetime | None = None

    @property
    def error(self) -> float:
        return self.goal_metric - self.observed_metric


@dataclass(frozen=True, slots=True)
class FeedbackDecision:
    signal: FeedbackSignal
    error: float
    rationale: str
    observed_at: datetime


class FeedbackController:
    """Small deterministic feedback controller for AGNES closed-loop planning.

    The controller only recommends a next control signal. It cannot execute actions or
    override CK-NEXUS policy/approval boundaries.
    """

    _HIGH_RISK = {"high", "critical"}

    def evaluate(self, observation: FeedbackObservation) -> FeedbackDecision:
        if observation.tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        observed_at = observation.observed_at or datetime.now(UTC)
        error = observation.error

        if observation.risk.lower() in self._HIGH_RISK and abs(error) > observation.tolerance:
            return FeedbackDecision(
                signal=FeedbackSignal.ASK_HUMAN,
                error=error,
                rationale="high-risk deviation exceeds tolerance",
                observed_at=observed_at,
            )
        if abs(error) <= observation.tolerance:
            return FeedbackDecision(
                signal=FeedbackSignal.CONTINUE,
                error=error,
                rationale="observed state is within goal tolerance",
                observed_at=observed_at,
            )
        if abs(error) > max(1.0, observation.tolerance * 4):
            return FeedbackDecision(
                signal=FeedbackSignal.REPLAN,
                error=error,
                rationale="deviation is large enough to require replanning",
                observed_at=observed_at,
            )
        return FeedbackDecision(
            signal=FeedbackSignal.CORRECT,
            error=error,
            rationale="bounded deviation can be corrected within the current plan",
            observed_at=observed_at,
        )
