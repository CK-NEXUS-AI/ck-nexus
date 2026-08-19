"""Opt-in proactive assistance policy with bounded notification behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum


class ProactiveStage(StrEnum):
    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


@dataclass(frozen=True, slots=True)
class ProactivePolicy:
    enabled: bool = False
    quiet_start: time | None = None
    quiet_end: time | None = None
    max_notifications_per_day: int = 3
    importance_threshold: float = 0.8
    allowed_channels: frozenset[str] = frozenset({"web"})
    autonomous_low_risk: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.max_notifications_per_day <= 100:
            raise ValueError("max_notifications_per_day must be between 0 and 100")
        if not 0.0 <= self.importance_threshold <= 1.0:
            raise ValueError("importance_threshold must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ProactiveProposal:
    kind: str
    importance: float
    channel: str
    stage: ProactiveStage = ProactiveStage.SUGGEST
    high_impact: bool = False
    external_write: bool = False


@dataclass(frozen=True, slots=True)
class ProactiveDecision:
    allowed: bool
    reason: str
    stage: ProactiveStage
    approval_required: bool


class ProactiveController:
    def __init__(self, policy: ProactivePolicy) -> None:
        self._policy = policy
        self._counts: dict[str, int] = {}

    def decide(
        self,
        proposal: ProactiveProposal,
        *,
        approved: bool = False,
        now: datetime | None = None,
    ) -> ProactiveDecision:
        current = now or datetime.now(UTC)
        day = current.date().isoformat()
        if not self._policy.enabled:
            return ProactiveDecision(False, "proactive_assistance_disabled", proposal.stage, True)
        if proposal.channel not in self._policy.allowed_channels:
            return ProactiveDecision(False, "channel_not_allowed", proposal.stage, True)
        if proposal.importance < self._policy.importance_threshold:
            return ProactiveDecision(False, "below_importance_threshold", proposal.stage, False)
        if self._in_quiet_hours(current.timetz().replace(tzinfo=None)):
            return ProactiveDecision(False, "quiet_hours", proposal.stage, False)
        if self._counts.get(day, 0) >= self._policy.max_notifications_per_day:
            return ProactiveDecision(False, "daily_notification_budget_exhausted", proposal.stage, False)

        approval_required = proposal.high_impact or proposal.external_write or proposal.stage == ProactiveStage.EXECUTE
        if approval_required and not approved:
            return ProactiveDecision(False, "explicit_approval_required", proposal.stage, True)

        if proposal.stage == ProactiveStage.EXECUTE and not self._policy.autonomous_low_risk and not approved:
            return ProactiveDecision(False, "execution_not_autonomous", proposal.stage, True)

        self._counts[day] = self._counts.get(day, 0) + 1
        return ProactiveDecision(True, "policy_allows", proposal.stage, approval_required)

    def _in_quiet_hours(self, current: time) -> bool:
        start = self._policy.quiet_start
        end = self._policy.quiet_end
        if start is None or end is None:
            return False
        if start <= end:
            return start <= current < end
        return current >= start or current < end
