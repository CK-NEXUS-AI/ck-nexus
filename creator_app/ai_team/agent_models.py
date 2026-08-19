"""Agent data models — โมเดลข้อมูลสำหรับ AI Expert Team."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentRole(Enum):
    DIRECTOR = "director"
    ENGINEER = "engineer"
    GUARDIAN = "guardian"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    DESIGNER = "designer"
    CONNECTOR = "connector"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class RequestPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass(frozen=True, slots=True)
class AgentCapability:
    name: str
    description: str
    level: int = 1  # 1-10 expertise level


@dataclass(slots=True)
class TaskResult:
    task_id: str
    agent_name: str
    agent_role: str
    status: TaskStatus
    output: str
    artifacts: tuple[str, ...] = ()
    duration_seconds: float = 0.0
    confidence: float = 0.0  # 0.0 - 1.0
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "status": self.status.value,
            "output": self.output,
            "artifacts": list(self.artifacts),
            "duration_seconds": self.duration_seconds,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class TeamRequest:
    request_id: str
    description: str
    priority: RequestPriority = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    context: str = ""
    constraints: tuple[str, ...] = ()


@dataclass(slots=True)
class TeamPlan:
    request_id: str
    steps: list[PlanStep] = field(default_factory=list)
    estimated_duration: float = 0.0
    created_at: float = field(default_factory=time.time)
    total_steps: int = 0


@dataclass(slots=True)
class PlanStep:
    step_id: str
    agent_name: str
    agent_role: str
    description: str
    depends_on: tuple[str, ...] = ()
    status: TaskStatus = TaskStatus.PENDING
    priority: RequestPriority = RequestPriority.NORMAL
    artifacts_expected: tuple[str, ...] = ()


@dataclass(slots=True)
class TeamResult:
    request_id: str
    final_output: str
    status: TaskStatus
    steps_completed: int
    steps_total: int
    team_members_used: tuple[str, ...] = ()
    duration_seconds: float = 0.0
    artifacts: tuple[str, ...] = ()
    confidence: float = 0.0
    plan: TeamPlan | None = None
    step_results: list[TaskResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "final_output": self.final_output,
            "status": self.status.value,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "team_members_used": list(self.team_members_used),
            "duration_seconds": self.duration_seconds,
            "artifacts": list(self.artifacts),
            "confidence": self.confidence,
        }


def generate_id(prefix: str = "id") -> str:
    """สร้าง ID ไม่ซ้ำ."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
