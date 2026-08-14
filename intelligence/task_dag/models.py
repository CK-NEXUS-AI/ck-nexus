from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class TaskNode:
    task_id: str
    capability: str
    dependencies: set[str] = field(default_factory=set)
    state: TaskState = TaskState.PENDING
    inputs: dict[str, object] = field(default_factory=dict)


@dataclass
class TaskDAG:
    tasks: dict[str, TaskNode] = field(default_factory=dict)

    def add(self, task: TaskNode) -> None:
        if task.task_id in task.dependencies:
            raise ValueError("task cannot depend on itself")
        self.tasks[task.task_id] = task

    def ready(self) -> list[TaskNode]:
        completed = {task_id for task_id, task in self.tasks.items() if task.state is TaskState.SUCCEEDED}
        return [
            task
            for task in self.tasks.values()
            if task.state is TaskState.PENDING and task.dependencies.issubset(completed)
        ]
