from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class UiState(StrEnum):
    IDLE = "idle"
    REQUESTED = "requested"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[UiState, frozenset[UiState]] = {
    UiState.IDLE: frozenset({UiState.REQUESTED}),
    UiState.REQUESTED: frozenset({UiState.RUNNING, UiState.BLOCKED, UiState.FAILED}),
    UiState.RUNNING: frozenset({UiState.VERIFYING, UiState.BLOCKED, UiState.FAILED}),
    UiState.VERIFYING: frozenset({UiState.COMPLETED, UiState.BLOCKED, UiState.FAILED}),
    UiState.COMPLETED: frozenset(),
    UiState.BLOCKED: frozenset(),
    UiState.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class UiStateEvent:
    event_id: str
    event_type: str
    current_state: UiState
    next_state: UiState
    task_id: str
    run_id: str
    correlation_id: str
    causation_id: str

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        required = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }
        failures.extend(name for name, value in required.items() if not value.strip())
        if self.next_state not in _ALLOWED_TRANSITIONS[self.current_state]:
            failures.append("invalid_state_transition")
        return tuple(failures)


def state_transition_allowed(current: UiState, next_state: UiState) -> bool:
    return next_state in _ALLOWED_TRANSITIONS[current]
