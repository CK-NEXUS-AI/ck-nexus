from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class ProgressDecision(str, Enum):
    CONTINUE = "CONTINUE"
    WARN = "WARN"
    CIRCUIT_BREAK = "CIRCUIT_BREAK"


@dataclass(frozen=True, slots=True)
class ProgressSample:
    step_index: int
    state_digest: str
    action_digest: str

    @classmethod
    def create(cls, step_index: int, state: dict[str, Any], action: dict[str, Any]) -> "ProgressSample":
        state_raw = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        action_raw = json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return cls(
            step_index=step_index,
            state_digest=hashlib.sha256(state_raw.encode()).hexdigest(),
            action_digest=hashlib.sha256(action_raw.encode()).hexdigest(),
        )


@dataclass(slots=True)
class NoProgressGuard:
    """Detect repeated agent cycles without claiming semantic correctness.

    The guard is deliberately deterministic: it only compares digests and
    bounded counters. It never authorizes or executes a recovery action.
    """

    warn_after: int = 2
    break_after: int = 3
    history_limit: int = 8
    history: list[ProgressSample] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.warn_after < 1:
            raise ValueError("warn_after must be >= 1")
        if self.break_after <= self.warn_after:
            raise ValueError("break_after must be greater than warn_after")
        if self.history_limit < self.break_after:
            raise ValueError("history_limit must be >= break_after")

    def observe(self, sample: ProgressSample) -> ProgressDecision:
        self.history.append(sample)
        if len(self.history) > self.history_limit:
            del self.history[:-self.history_limit]

        repeated = 1
        for previous in reversed(self.history[:-1]):
            if (
                previous.state_digest == sample.state_digest
                and previous.action_digest == sample.action_digest
            ):
                repeated += 1
            else:
                break

        if repeated >= self.break_after:
            return ProgressDecision.CIRCUIT_BREAK
        if repeated >= self.warn_after:
            return ProgressDecision.WARN
        return ProgressDecision.CONTINUE

    def reset(self) -> None:
        self.history.clear()
