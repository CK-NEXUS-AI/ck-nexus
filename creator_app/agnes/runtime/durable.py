from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class DurableRunState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class DurableCheckpoint:
    run_id: str
    step_index: int
    state: dict[str, Any]
    digest: str

    @classmethod
    def create(cls, run_id: str, step_index: int, state: dict[str, Any]) -> "DurableCheckpoint":
        canonical = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(f"{run_id}:{step_index}:{canonical}".encode()).hexdigest()
        return cls(run_id=run_id, step_index=step_index, state=dict(state), digest=digest)


@dataclass(slots=True)
class DurableRun:
    run_id: str
    state: DurableRunState = DurableRunState.PENDING
    step_index: int = 0
    logical_state: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[DurableCheckpoint] = field(default_factory=list)

    def start(self) -> None:
        if self.state not in {DurableRunState.PENDING, DurableRunState.PAUSED}:
            raise ValueError(f"cannot start from {self.state}")
        self.state = DurableRunState.RUNNING

    def advance(self, patch: dict[str, Any]) -> DurableCheckpoint:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("run must be RUNNING before advance")
        self.logical_state.update(patch)
        self.step_index += 1
        checkpoint = DurableCheckpoint.create(self.run_id, self.step_index, self.logical_state)
        self.checkpoints.append(checkpoint)
        return checkpoint

    def pause(self) -> DurableCheckpoint:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("only RUNNING run can pause")
        checkpoint = DurableCheckpoint.create(self.run_id, self.step_index, self.logical_state)
        self.checkpoints.append(checkpoint)
        self.state = DurableRunState.PAUSED
        return checkpoint

    def restore(self, checkpoint: DurableCheckpoint) -> None:
        if checkpoint.run_id != self.run_id:
            raise ValueError("checkpoint belongs to another run")
        expected = DurableCheckpoint.create(checkpoint.run_id, checkpoint.step_index, checkpoint.state)
        if expected.digest != checkpoint.digest:
            raise ValueError("checkpoint digest mismatch")
        self.step_index = checkpoint.step_index
        self.logical_state = dict(checkpoint.state)
        self.state = DurableRunState.PAUSED

    def complete(self) -> None:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("run must be RUNNING before completion")
        self.state = DurableRunState.COMPLETED
