"""Reflexion — สะท้อนคิดและเรียนรู้จากความผิดพลาด.

เทคนิค Reflexion ให้ Agent:
1. ทำงานเสร็จ → ประเมินผลลัพธ์
2. หาจุดผิดพลาด → วิเคราะห์สาเหตุ
3. สร้าง feedback → ส่งกลับรอบถัดไป
4. ปรับปรุงตัวเอง → ไม่ต้อง fine-tune ใหม่

อ้างอิง:
- reflexion-agent-boilerplate
- Agent-R (ByteDance)
- RetroAct (IL + RL)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ReflectionOutcome(str, Enum):
    """ผลลัพธ์จากการสะท้อนคิด."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    NEEDS_REVISION = "needs_revision"


@dataclass
class ReflectionEntry:
    """รายการสะท้อนคิดหนึ่งครั้ง."""
    task_id: str
    agent_role: str
    action_taken: str
    expected_outcome: str
    actual_outcome: str
    outcome: ReflectionOutcome
    error_analysis: str = ""
    improvement_suggestion: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionPattern:
    """รูปแบบที่พบจากการสะท้อนคิด."""
    pattern_id: str
    description: str
    frequency: int = 0
    affected_roles: list[str] = field(default_factory=list)
    suggested_fix: str = ""
    severity: str = "low"  # low, medium, high, critical


class SelfEvaluator(Protocol):
    """โปรโตคอลสำหรับ Agent ที่สามารถประเมินตัวเองได้."""

    def evaluate(self, action: str, result: str) -> ReflectionOutcome:
        """ประเมินผลลัพธ์ของการกระทำ."""
        ...

    def suggest_improvement(self, entry: ReflectionEntry) -> str:
        """แนะนำการปรับปรุง."""
        ...


class ReflexionEngine:
    """เครื่องยนต์ Reflexion — สะท้อนคิดและเรียนรู้.

    วิธีใช้:
        engine = ReflexionEngine()

        # บันทึกผลลัพธ์
        entry = engine.record(
            task_id="task-001",
            agent_role="coder",
            action="เขียนฟังก์ชัน validate_email",
            expected="return True สำหรับ email ที่ถูกต้อง",
            actual="return True สำหรับทุก string",
            outcome=ReflectionOutcome.FAILURE,
            error_analysis="ไม่ได้เช็ค regex pattern",
        )

        # ดูรูปแบบที่พบ
        patterns = engine.analyze_patterns()

        # รับ feedback สำหรับรอบถัดไป
        feedback = engine.get_feedback_for_role("coder")
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._history: list[ReflectionEntry] = []
        self._patterns: list[ReflectionPattern] = []
        self._max_history = max_history
        self._feedback_cache: dict[str, list[str]] = {}

    def record(
        self,
        task_id: str,
        agent_role: str,
        action: str,
        expected_outcome: str,
        actual_outcome: str,
        outcome: ReflectionOutcome,
        error_analysis: str = "",
        improvement_suggestion: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ReflectionEntry:
        """บันทึกผลลัพธ์จากการกระทำ."""
        entry = ReflectionEntry(
            task_id=task_id,
            agent_role=agent_role,
            action_taken=action,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            outcome=outcome,
            error_analysis=error_analysis,
            improvement_suggestion=improvement_suggestion,
            metadata=metadata or {},
        )
        self._history.append(entry)

        # ตัด history เก่าออกถ้าเกิน max
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # อัปเดต feedback cache
        if agent_role not in self._feedback_cache:
            self._feedback_cache[agent_role] = []
        if improvement_suggestion:
            self._feedback_cache[agent_role].append(improvement_suggestion)

        # ตรวจรูปแบบ
        self._detect_patterns(entry)

        return entry

    def get_feedback_for_role(self, role: str, limit: int = 5) -> list[str]:
        """ดึง feedback ล่าสุดสำหรับบทบาทหนึ่ง."""
        feedbacks = self._feedback_cache.get(role, [])
        return feedbacks[-limit:]

    def get_stats_for_role(self, role: str) -> dict[str, Any]:
        """ดึงสถิติสำหรับบทบาทหนึ่ง."""
        role_entries = [e for e in self._history if e.agent_role == role]
        if not role_entries:
            return {"total": 0}

        outcomes = {}
        for e in role_entries:
            outcomes[e.outcome.value] = outcomes.get(e.outcome.value, 0) + 1

        total = len(role_entries)
        success_rate = outcomes.get("success", 0) / total * 100

        return {
            "total": total,
            "success_rate": round(success_rate, 1),
            "outcomes": outcomes,
            "recent_errors": [
                e.error_analysis for e in role_entries
                if e.outcome in (ReflectionOutcome.FAILURE, ReflectionOutcome.NEEDS_REVISION)
            ][-3:],
        }

    def analyze_patterns(self) -> list[ReflectionPattern]:
        """วิเคราะห์รูปแบบที่พบจากการสะท้อนคิด."""
        return [p for p in self._patterns if p.frequency >= 2]

    def _detect_patterns(self, entry: ReflectionEntry) -> None:
        """ตรวจจับรูปแบบจาก entry ใหม่."""
        if entry.outcome not in (ReflectionOutcome.FAILURE, ReflectionOutcome.NEEDS_REVISION):
            return

        # ตรวจว่ามี pattern ที่คล้ายกันอยู่แล้วหรือไม่
        for pattern in self._patterns:
            if self._similar_error(entry.error_analysis, pattern.description):
                pattern.frequency += 1
                if entry.agent_role not in pattern.affected_roles:
                    pattern.affected_roles.append(entry.agent_role)
                return

        # สร้าง pattern ใหม่
        new_pattern = ReflectionPattern(
            pattern_id=f"pat-{len(self._patterns) + 1:04d}",
            description=entry.error_analysis[:200],
            frequency=1,
            affected_roles=[entry.agent_role],
            suggested_fix=entry.improvement_suggestion,
        )
        self._patterns.append(new_pattern)

    @staticmethod
    def _similar_error(error1: str, error2: str) -> bool:
        """ตรวจสอบว่า error สองตัวคล้ายกันหรือไม่ (แบบง่าย)."""
        if not error1 or not error2:
            return False
        words1 = set(error1.lower().split())
        words2 = set(error2.lower().split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / min(len(words1), len(words2))
        return overlap > 0.5

    def summary(self) -> dict[str, Any]:
        """สรุปผลทั้งหมด."""
        total = len(self._history)
        if total == 0:
            return {"total": 0, "message": "ยังไม่มีรายการสะท้อนคิด"}

        outcomes = {}
        for e in self._history:
            outcomes[e.outcome.value] = outcomes.get(e.outcome.value, 0) + 1

        roles = set(e.agent_role for e in self._history)

        return {
            "total": total,
            "outcomes": outcomes,
            "roles": list(roles),
            "patterns_found": len(self._patterns),
            "patterns_above_threshold": len(self.analyze_patterns()),
        }

    def export_history(self) -> list[dict[str, Any]]:
        """ส่งออกประวัติทั้งหมด."""
        return [
            {
                "task_id": e.task_id,
                "agent_role": e.agent_role,
                "action": e.action_taken,
                "outcome": e.outcome.value,
                "error": e.error_analysis,
                "improvement": e.improvement_suggestion,
                "timestamp": e.timestamp,
            }
            for e in self._history
        ]


def create_reflexion_for_agent(role: str) -> ReflexionEngine:
    """สร้าง ReflexionEngine สำหรับ Agent บทบาทหนึ่ง."""
    engine = ReflexionEngine()
    return engine
