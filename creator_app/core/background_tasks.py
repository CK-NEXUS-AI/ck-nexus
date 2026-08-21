from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BackgroundTaskState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundTask(BaseModel):
    task_id: str
    subject: str
    state: BackgroundTaskState = BackgroundTaskState.QUEUED
    checkpoint_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    execution_grant_id: str | None = None


class BackgroundTaskController:
    """State contract for durable work; execution remains delegated."""

    def start(self, task: BackgroundTask) -> BackgroundTask:
        if not task.execution_grant_id:
            raise ValueError("background task requires execution_grant_id")
        if task.state != BackgroundTaskState.QUEUED:
            raise ValueError("only queued tasks may start")
        task.state = BackgroundTaskState.RUNNING
        task.updated_at = datetime.now(UTC)
        return task

    def suspend(self, task: BackgroundTask, *, checkpoint_id: str) -> BackgroundTask:
        if task.state != BackgroundTaskState.RUNNING:
            raise ValueError("only running tasks may suspend")
        task.state = BackgroundTaskState.SUSPENDED
        task.checkpoint_id = checkpoint_id
        task.updated_at = datetime.now(UTC)
        return task

    def resume(self, task: BackgroundTask) -> BackgroundTask:
        if task.state != BackgroundTaskState.SUSPENDED or not task.checkpoint_id:
            raise ValueError("resume requires suspended task with checkpoint")
        if not task.execution_grant_id:
            raise ValueError("resume requires execution_grant_id")
        task.state = BackgroundTaskState.RUNNING
        task.updated_at = datetime.now(UTC)
        return task
