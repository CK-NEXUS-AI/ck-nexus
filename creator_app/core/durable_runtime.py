from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DurableTaskState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Checkpoint(BaseModel):
    checkpoint_id: str
    subject: str
    state_digest: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DurableTask(BaseModel):
    task_id: str
    subject: str
    state: DurableTaskState = DurableTaskState.PENDING
    checkpoint_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    resume_token_ref: str | None = None
    production_promotion_allowed: bool = False


class DurableRuntimePolicy:
    """Provider-neutral, fail-closed policy for long-running work."""

    @staticmethod
    def can_resume(task: DurableTask) -> bool:
        return (
            task.state == DurableTaskState.SUSPENDED
            and bool(task.checkpoint_ids)
            and bool(task.resume_token_ref)
        )

    @staticmethod
    def can_fork(task: DurableTask) -> bool:
        return task.state in {DurableTaskState.SUSPENDED, DurableTaskState.COMPLETED} and bool(
            task.checkpoint_ids
        )
