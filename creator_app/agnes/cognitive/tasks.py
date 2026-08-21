"""Durable task contracts independent from any executor implementation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class TaskState(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_ALLOWED: dict[TaskState, frozenset[TaskState]] = {
    TaskState.CREATED: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.READY: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.RUNNING: frozenset(
        {TaskState.PAUSED, TaskState.WAITING_HUMAN, TaskState.VERIFYING, TaskState.FAILED, TaskState.CANCELLED}
    ),
    TaskState.PAUSED: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.WAITING_HUMAN: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.VERIFYING: frozenset({TaskState.SUCCEEDED, TaskState.FAILED}),
    TaskState.SUCCEEDED: frozenset(),
    TaskState.FAILED: frozenset({TaskState.READY, TaskState.CANCELLED}),
    TaskState.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class DurableTask:
    task_id: str
    goal: str
    owner: str
    state: TaskState = TaskState.CREATED
    checkpoint_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    retry_count: int = 0


class DurableTaskRuntime:
    def transition(self, task: DurableTask, target: TaskState) -> DurableTask:
        if target not in _ALLOWED[task.state]:
            raise ValueError(f"invalid task transition: {task.state} -> {target}")
        return replace(task, state=target)

    def checkpoint(self, task: DurableTask, checkpoint_ref: str) -> DurableTask:
        if task.state not in {TaskState.RUNNING, TaskState.PAUSED, TaskState.WAITING_HUMAN}:
            raise ValueError("checkpoint is only valid for active or paused tasks")
        return replace(task, checkpoint_ref=checkpoint_ref)

    def retry(self, task: DurableTask) -> DurableTask:
        if task.state is not TaskState.FAILED:
            raise ValueError("only failed tasks can retry")
        return replace(task, state=TaskState.READY, retry_count=task.retry_count + 1)
