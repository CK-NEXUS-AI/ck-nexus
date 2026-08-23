from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any


def _canonical_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class SignalState(str, Enum):
    PENDING = "PENDING"
    CONSUMED = "CONSUMED"


@dataclass(slots=True)
class DurableSignal:
    signal_id: str
    name: str
    payload: dict[str, Any]
    state: SignalState = SignalState.PENDING

    @property
    def digest(self) -> str:
        return _canonical_digest({
            "signal_id": self.signal_id,
            "name": self.name,
            "payload": self.payload,
        })


class TimerState(str, Enum):
    SCHEDULED = "SCHEDULED"
    FIRED = "FIRED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class DurableTimer:
    timer_id: str
    due_at: datetime
    state: TimerState = TimerState.SCHEDULED

    def __post_init__(self) -> None:
        if self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")
        self.due_at = self.due_at.astimezone(timezone.utc)

    def fire_if_due(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if self.state is not TimerState.SCHEDULED:
            return False
        if now.astimezone(timezone.utc) < self.due_at:
            return False
        self.state = TimerState.FIRED
        return True

    def cancel(self) -> None:
        if self.state is not TimerState.SCHEDULED:
            raise ValueError(f"cannot cancel timer from {self.state}")
        self.state = TimerState.CANCELLED


class CompensationState(str, Enum):
    REGISTERED = "REGISTERED"
    COMPENSATED = "COMPENSATED"


@dataclass(slots=True)
class CompensationRecord:
    action_id: str
    action_digest: str
    compensation_name: str
    state: CompensationState = CompensationState.REGISTERED


@dataclass(slots=True)
class DurableControlPlane:
    """Deterministic durable controls with no background or external execution.

    Signals are idempotent by signal_id. Timers fire only when a caller supplies
    an explicit clock value. Compensations are planned in reverse registration
    order and must be explicitly acknowledged after an external executor runs
    them under CK-NEXUS governance.
    """

    signals: dict[str, DurableSignal] = field(default_factory=dict)
    timers: dict[str, DurableTimer] = field(default_factory=dict)
    compensations: list[CompensationRecord] = field(default_factory=list)

    def deliver_signal(self, signal_id: str, name: str, payload: dict[str, Any]) -> DurableSignal:
        existing = self.signals.get(signal_id)
        candidate = DurableSignal(signal_id, name, dict(payload))
        if existing is not None:
            if existing.digest != candidate.digest:
                raise ValueError("signal_id replayed with different content")
            return existing
        self.signals[signal_id] = candidate
        return candidate

    def consume_signal(self, signal_id: str) -> DurableSignal:
        signal = self.signals.get(signal_id)
        if signal is None:
            raise KeyError(signal_id)
        if signal.state is SignalState.CONSUMED:
            raise ValueError("signal already consumed")
        signal.state = SignalState.CONSUMED
        return signal

    def schedule_timer(self, timer_id: str, due_at: datetime) -> DurableTimer:
        existing = self.timers.get(timer_id)
        candidate = DurableTimer(timer_id, due_at)
        if existing is not None:
            if existing.due_at != candidate.due_at:
                raise ValueError("timer_id replayed with different due_at")
            return existing
        self.timers[timer_id] = candidate
        return candidate

    def fire_due_timers(self, now: datetime) -> tuple[str, ...]:
        fired: list[str] = []
        for timer_id in sorted(self.timers):
            if self.timers[timer_id].fire_if_due(now):
                fired.append(timer_id)
        return tuple(fired)

    def register_compensation(
        self,
        action_id: str,
        action_digest: str,
        compensation_name: str,
    ) -> CompensationRecord:
        for record in self.compensations:
            if record.action_id == action_id:
                if (record.action_digest, record.compensation_name) != (action_digest, compensation_name):
                    raise ValueError("action_id compensation replay mismatch")
                return record
        record = CompensationRecord(action_id, action_digest, compensation_name)
        self.compensations.append(record)
        return record

    def compensation_plan(self) -> tuple[CompensationRecord, ...]:
        return tuple(
            record
            for record in reversed(self.compensations)
            if record.state is CompensationState.REGISTERED
        )

    def mark_compensated(self, action_id: str) -> None:
        for record in self.compensations:
            if record.action_id == action_id:
                if record.state is CompensationState.COMPENSATED:
                    raise ValueError("action already compensated")
                record.state = CompensationState.COMPENSATED
                return
        raise KeyError(action_id)
