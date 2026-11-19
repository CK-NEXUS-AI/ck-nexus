"""Agent base class — ฐานของ AI ผู้เชี่ยวชาญทุกคน."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from creator_app.ai_team.agent_models import (
    AgentCapability,
    AgentRole,
    TaskResult,
    TaskStatus,
    TeamRequest,
)
from creator_app.ai_team.cancellation import raise_if_cancelled


@dataclass
class AgentKnowledge:
    """ความรู้ที่ Agent สะสมจากการทำงาน."""

    completed_tasks: int = 0
    total_tasks: int = 0
    success_rate: float = 0.0
    learned_patterns: list[str] = field(default_factory=list)
    last_error: str = ""
    avg_confidence: float = 0.0


class Agent(ABC):
    """Base class สำหรับ AI ผู้เชี่ยวชาญทุกคน.

    แต่ละ Agent จะมี:
    - ชื่อ, บทบาท, ความเชี่ยวชาญ
    - วิธีประมวลผลงานของตัวเอง
    - ความรู้ที่สะสมจากการทำงาน
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        expertise: tuple[str, ...] = (),
        description: str = "",
        capabilities: tuple[AgentCapability, ...] = (),
    ) -> None:
        self.name = name
        self.role = role
        self.expertise = tuple(expertise)
        self.description = description or f"{self.name} — {self.role.value}"
        self.capabilities = tuple(capabilities)
        self.knowledge = AgentKnowledge()
        self._active = True

    @staticmethod
    def raise_if_cancelled(context: dict[str, Any] | None) -> None:
        """Check the request cancellation event at a worker-safe checkpoint."""
        event = context.get("cancellation_event") if context else None
        raise_if_cancelled(event)

    @abstractmethod
    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        """ประมวลผลงาน — แต่ละ Agent จะมีวิธีต่างกัน."""
        ...

    def can_handle(self, keywords: tuple[str, ...]) -> bool:
        """ตรวจสอบว่า Agent นี้สามารถจัดการกับคำสำคัญได้หรือไม่."""
        expertise_lower = tuple(e.lower() for e in self.expertise)
        return any(kw.lower() in expertise_lower for kw in keywords)

    def confidence_for(self, keywords: tuple[str, ...]) -> float:
        """คำนวณความมั่นใจในการรับงาน (0.0 - 1.0)."""
        if not keywords:
            return 0.0
        matched = sum(1 for kw in keywords if any(kw.lower() in e.lower() for e in self.expertise))
        return matched / len(keywords)

    def record_result(self, result: TaskResult) -> None:
        """บันทึกผลลัพธ์เพื่อเรียนรู้."""
        self.knowledge.total_tasks += 1
        if result.status == TaskStatus.COMPLETED:
            self.knowledge.completed_tasks += 1
        else:
            self.knowledge.last_error = result.output

        n = self.knowledge.total_tasks
        self.knowledge.success_rate = self.knowledge.completed_tasks / n if n > 0 else 0.0
        total_conf = self.knowledge.avg_confidence * (n - 1) + result.confidence
        self.knowledge.avg_confidence = total_conf / n

    def status(self) -> dict[str, Any]:
        """สถานะของ Agent."""
        return {
            "name": self.name,
            "role": self.role.value,
            "active": self._active,
            "expertise": list(self.expertise),
            "capabilities": [c.name for c in self.capabilities],
            "description": self.description,
            "knowledge": {
                "total_tasks": self.knowledge.total_tasks,
                "success_rate": self.knowledge.success_rate,
                "avg_confidence": self.knowledge.avg_confidence,
            },
        }

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role.value!r})"
