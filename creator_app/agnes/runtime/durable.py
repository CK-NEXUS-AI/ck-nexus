from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable


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
    parent_digest: str | None = None
    pending_writes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        run_id: str,
        step_index: int,
        state: dict[str, Any],
        *,
        parent_digest: str | None = None,
        pending_writes: dict[str, Any] | None = None,
    ) -> "DurableCheckpoint":
        state_copy = deepcopy(state)
        writes_copy = deepcopy(pending_writes or {})
        payload = {
            "run_id": run_id,
            "step_index": step_index,
            "state": state_copy,
            "parent_digest": parent_digest,
            "pending_writes": writes_copy,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(
            run_id=run_id,
            step_index=step_index,
            state=state_copy,
            digest=digest,
            parent_digest=parent_digest,
            pending_writes=writes_copy,
        )

    def verify(self) -> bool:
        expected = DurableCheckpoint.create(
            self.run_id,
            self.step_index,
            self.state,
            parent_digest=self.parent_digest,
            pending_writes=self.pending_writes,
        )
        return expected.digest == self.digest


@dataclass(slots=True)
class DurableRun:
    run_id: str
    state: DurableRunState = DurableRunState.PENDING
    step_index: int = 0
    logical_state: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[DurableCheckpoint] = field(default_factory=list)
    pending_writes: dict[str, Any] = field(default_factory=dict)
    origin_checkpoint_digest: str | None = None

    def start(self) -> None:
        if self.state not in {DurableRunState.PENDING, DurableRunState.PAUSED}:
            raise ValueError(f"cannot start from {self.state}")
        self.state = DurableRunState.RUNNING

    @property
    def latest_checkpoint(self) -> DurableCheckpoint | None:
        return self.checkpoints[-1] if self.checkpoints else None

    def stage_write(self, key: str, value: Any) -> None:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("run must be RUNNING before staging writes")
        self.pending_writes[str(key)] = deepcopy(value)

    def clear_pending_writes(self) -> None:
        self.pending_writes.clear()

    def _checkpoint(self) -> DurableCheckpoint:
        parent_digest = self.latest_checkpoint.digest if self.latest_checkpoint else self.origin_checkpoint_digest
        checkpoint = DurableCheckpoint.create(
            self.run_id,
            self.step_index,
            self.logical_state,
            parent_digest=parent_digest,
            pending_writes=self.pending_writes,
        )
        self.checkpoints.append(checkpoint)
        return checkpoint

    def advance(self, patch: dict[str, Any]) -> DurableCheckpoint:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("run must be RUNNING before advance")
        self.logical_state.update(deepcopy(patch))
        self.step_index += 1
        return self._checkpoint()

    def pause(self) -> DurableCheckpoint:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("only RUNNING run can pause")
        checkpoint = self._checkpoint()
        self.state = DurableRunState.PAUSED
        return checkpoint

    def restore(self, checkpoint: DurableCheckpoint) -> None:
        if checkpoint.run_id != self.run_id:
            raise ValueError("checkpoint belongs to another run")
        if not checkpoint.verify():
            raise ValueError("checkpoint digest mismatch")
        self.step_index = checkpoint.step_index
        self.logical_state = deepcopy(checkpoint.state)
        self.pending_writes = deepcopy(checkpoint.pending_writes)
        self.state = DurableRunState.PAUSED

    def replay_to(self, step_index: int) -> DurableCheckpoint:
        candidates = [cp for cp in self.checkpoints if cp.step_index == step_index]
        if not candidates:
            raise ValueError(f"no checkpoint for step {step_index}")
        checkpoint = candidates[-1]
        self.restore(checkpoint)
        return checkpoint

    def fork(self, new_run_id: str, checkpoint: DurableCheckpoint | None = None) -> "DurableRun":
        source = checkpoint or self.latest_checkpoint
        if source is None:
            raise ValueError("cannot fork without a checkpoint")
        if not source.verify():
            raise ValueError("cannot fork from invalid checkpoint")
        return DurableRun(
            run_id=new_run_id,
            state=DurableRunState.PAUSED,
            step_index=source.step_index,
            logical_state=deepcopy(source.state),
            pending_writes=deepcopy(source.pending_writes),
            origin_checkpoint_digest=source.digest,
        )

    def complete(self) -> None:
        if self.state is not DurableRunState.RUNNING:
            raise ValueError("run must be RUNNING before completion")
        if self.pending_writes:
            raise ValueError("cannot complete with uncommitted pending writes")
        self.state = DurableRunState.COMPLETED

    def fail(self) -> None:
        if self.state not in {DurableRunState.RUNNING, DurableRunState.PAUSED}:
            raise ValueError(f"cannot fail from {self.state}")
        self.state = DurableRunState.FAILED

    @staticmethod
    def verify_lineage(checkpoints: Iterable[DurableCheckpoint]) -> bool:
        ordered = list(checkpoints)
        previous: DurableCheckpoint | None = None
        for checkpoint in ordered:
            if not checkpoint.verify():
                return False
            if previous is not None and checkpoint.parent_digest != previous.digest:
                return False
            previous = checkpoint
        return True
