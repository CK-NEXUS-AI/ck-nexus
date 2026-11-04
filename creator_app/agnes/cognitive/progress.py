from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ProgressState(StrEnum):
    NOT_STARTED = "not_started"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    EXECUTING = "executing"
    PARTIAL_SUCCESS = "partial_success"
    VERIFYING = "verifying"
    SUCCESS = "success"
    STALLED = "stalled"
    DRIFTING = "drifting"
    LOOPING = "looping"
    WRONG_GOAL = "wrong_goal"
    FALSE_SUCCESS = "false_success"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    WAITING_HUMAN = "waiting_human"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL = {ProgressState.SUCCESS, ProgressState.FAILED, ProgressState.CANCELLED}

_ALLOWED: dict[ProgressState, set[ProgressState]] = {
    ProgressState.NOT_STARTED: {ProgressState.UNDERSTANDING, ProgressState.CANCELLED},
    ProgressState.UNDERSTANDING: {
        ProgressState.PLANNING,
        ProgressState.WAITING_HUMAN,
        ProgressState.WRONG_GOAL,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.PLANNING: {
        ProgressState.EXECUTING,
        ProgressState.WAITING_HUMAN,
        ProgressState.DEPENDENCY_BLOCKED,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.EXECUTING: {
        ProgressState.PARTIAL_SUCCESS,
        ProgressState.VERIFYING,
        ProgressState.STALLED,
        ProgressState.DRIFTING,
        ProgressState.LOOPING,
        ProgressState.DEPENDENCY_BLOCKED,
        ProgressState.WAITING_HUMAN,
        ProgressState.RESOURCE_EXHAUSTED,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.PARTIAL_SUCCESS: {
        ProgressState.EXECUTING,
        ProgressState.VERIFYING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.VERIFYING: {
        ProgressState.SUCCESS,
        ProgressState.FALSE_SUCCESS,
        ProgressState.EXECUTING,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.STALLED: {
        ProgressState.EXECUTING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.DRIFTING: {
        ProgressState.PLANNING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.LOOPING: {
        ProgressState.PLANNING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.WRONG_GOAL: {
        ProgressState.UNDERSTANDING,
        ProgressState.WAITING_HUMAN,
        ProgressState.CANCELLED,
    },
    ProgressState.FALSE_SUCCESS: {
        ProgressState.PLANNING,
        ProgressState.EXECUTING,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.DEPENDENCY_BLOCKED: {
        ProgressState.PLANNING,
        ProgressState.EXECUTING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.WAITING_HUMAN: {
        ProgressState.UNDERSTANDING,
        ProgressState.PLANNING,
        ProgressState.EXECUTING,
        ProgressState.CANCELLED,
    },
    ProgressState.RESOURCE_EXHAUSTED: {
        ProgressState.PLANNING,
        ProgressState.WAITING_HUMAN,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    },
    ProgressState.SUCCESS: set(),
    ProgressState.FAILED: set(),
    ProgressState.CANCELLED: set(),
}


@dataclass(frozen=True, slots=True)
class ProgressTransition:
    previous: ProgressState
    current: ProgressState
    reason: str
    observed_at: datetime


class ProgressIntelligence:
    """Fail-closed task progress state machine.

    Invalid transitions raise instead of being silently accepted. A successful state is
    reachable only through VERIFYING, so execution cannot self-declare success directly.
    """

    def __init__(self) -> None:
        self._state = ProgressState.NOT_STARTED
        self._history: list[ProgressTransition] = []

    @property
    def state(self) -> ProgressState:
        return self._state

    @property
    def terminal(self) -> bool:
        return self._state in _TERMINAL

    def transition(self, target: ProgressState, reason: str) -> ProgressTransition:
        if not reason.strip():
            raise ValueError("transition reason is required")
        if target not in _ALLOWED[self._state]:
            raise ValueError(f"invalid progress transition: {self._state} -> {target}")
        transition = ProgressTransition(
            previous=self._state,
            current=target,
            reason=reason.strip(),
            observed_at=datetime.now(UTC),
        )
        self._state = target
        self._history.append(transition)
        return transition

    def history(self) -> tuple[ProgressTransition, ...]:
        return tuple(self._history)
