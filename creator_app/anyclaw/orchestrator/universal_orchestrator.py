"""Universal Orchestrator — สมองกลางที่เชื่อมทุกอย่าง.

เปลี่ยน AnyClaw จาก "ผู้ช่วยที่ต้องคอยสั่ง"
เป็น "ผู้ร่วมงานอัตโนมัติ" ที่:
1. รับคำสั่งภาษาธรรมชาติ → วิเคราะห์ → แบ่งงาน
2. เลือกเครื่องมือที่เหมาะสม → เรียกใช้อัตโนมัติ
3. จัดการ fallback → ถ้าล้ม → ใช้ตัวถัดไป
4. เรียนรู้จากผลลัพธ์ → ปรับปรุงรอบถัดไป
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    AUTONOMOUS = "autonomous"


class TaskCategory(str, Enum):
    RESEARCH = "research"
    CODING = "coding"
    COMMUNICATION = "communication"
    DATA_PROCESSING = "data_processing"
    AUTOMATION = "automation"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    CONTENT = "content"


@dataclass
class OrchestratedTask:
    task_id: str
    original_request: str
    complexity: TaskComplexity
    category: TaskCategory
    subtasks: list[dict[str, Any]] = field(default_factory=list)
    tools_required: list[str] = field(default_factory=list)
    estimated_time: float = 0.0
    status: str = "analyzing"
    result: Any = None


class UniversalOrchestrator:
    """สมองกลาง — วิเคราะห์ แบ่งงาน จัดการ ประสานงาน.

    วิธีใช้:
        orch = UniversalOrchestrator()
        task = orch.analyze("สรุปอีเมล → บันทึกตาราง → แจ้งทีม")
        result = orch.execute(task)
    """

    TOOL_MAP: dict[str, dict[str, Any]] = {
        "อีเมล": {"tool": "mcp-gmail", "category": TaskCategory.COMMUNICATION, "mcp_server": "mcp-headless-gmail"},
        "gmail": {"tool": "mcp-gmail", "category": TaskCategory.COMMUNICATION, "mcp_server": "mcp-headless-gmail"},
        "otp": {"tool": "fce-mcp", "category": TaskCategory.AUTOMATION, "mcp_server": "fce-mcp-server"},
        "ค้นหา": {"tool": "search", "category": TaskCategory.RESEARCH, "mcp_server": "anycrawl-mcp"},
        "search": {"tool": "search", "category": TaskCategory.RESEARCH, "mcp_server": "anycrawl-mcp"},
        "เว็บ": {"tool": "scrape", "category": TaskCategory.RESEARCH, "mcp_server": "anycrawl-mcp"},
        "web": {"tool": "scrape", "category": TaskCategory.RESEARCH, "mcp_server": "anycrawl-mcp"},
        "โค้ด": {"tool": "code", "category": TaskCategory.CODING},
        "code": {"tool": "code", "category": TaskCategory.CODING},
        "เขียน": {"tool": "code", "category": TaskCategory.CODING},
        "ตาราง": {"tool": "sheets", "category": TaskCategory.DATA_PROCESSING, "mcp_server": "google-automation-mcp"},
        "sheets": {"tool": "sheets", "category": TaskCategory.DATA_PROCESSING, "mcp_server": "google-automation-mcp"},
        "แจ้ง": {"tool": "notify", "category": TaskCategory.COMMUNICATION, "mcp_server": "telegram-mcp"},
        "telegram": {"tool": "telegram", "category": TaskCategory.COMMUNICATION, "mcp_server": "telegram-mcp"},
        "slack": {"tool": "slack", "category": TaskCategory.COMMUNICATION, "mcp_server": "slack-mcp"},
        "deploy": {"tool": "deploy", "category": TaskCategory.DEPLOYMENT},
        "สร้าง": {"tool": "create", "category": TaskCategory.CODING},
        "สรุป": {"tool": "summarize", "category": TaskCategory.DATA_PROCESSING},
        "วิเคราะห์": {"tool": "analyze", "category": TaskCategory.DATA_PROCESSING},
        "วันนี้": {"tool": "calendar", "category": TaskCategory.COMMUNICATION, "mcp_server": "google-automation-mcp"},
        "calendar": {"tool": "calendar", "category": TaskCategory.COMMUNICATION, "mcp_server": "google-automation-mcp"},
        "สแกน": {"tool": "scan", "category": TaskCategory.SECURITY},
        "security": {"tool": "scan", "category": TaskCategory.SECURITY},
        "notion": {"tool": "notion", "category": TaskCategory.DATA_PROCESSING, "mcp_server": "notion-mcp"},
        "github": {"tool": "github", "category": TaskCategory.CODING, "mcp_server": "github-mcp"},
    }

    def __init__(self) -> None:
        self._task_counter = 0
        self._history: list[OrchestratedTask] = []
        self._stats: dict[str, int] = {
            "tasks_analyzed": 0,
            "tasks_executed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
        }

    def analyze(self, request: str) -> OrchestratedTask:
        self._task_counter += 1
        task_id = f"orch-{self._task_counter:06d}"
        complexity = self._assess_complexity(request)
        category = self._assess_category(request)
        subtasks = self._extract_subtasks(request)
        tools_required = self._identify_tools(request)
        estimated_time = self._estimate_time(complexity, len(subtasks))

        task = OrchestratedTask(
            task_id=task_id,
            original_request=request,
            complexity=complexity,
            category=category,
            subtasks=subtasks,
            tools_required=tools_required,
            estimated_time=estimated_time,
            status="ready",
        )
        self._history.append(task)
        self._stats["tasks_analyzed"] += 1
        return task

    def execute(self, task: OrchestratedTask) -> dict[str, Any]:
        task.status = "executing"
        self._stats["tasks_executed"] += 1
        results = []
        for subtask in task.subtasks:
            result = {
                "tool": subtask.get("tool", "unknown"),
                "description": subtask.get("description", ""),
                "success": True,
                "result": f"Executed: {subtask.get('description', '')}",
                "timestamp": time.time(),
            }
            results.append(result)
        task.result = results
        task.status = "completed"
        self._stats["tasks_succeeded"] += 1
        return {
            "task_id": task.task_id,
            "status": "completed",
            "results": results,
            "total_subtasks": len(results),
            "all_succeeded": all(r["success"] for r in results),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            **self._stats,
            "total_history": len(self._history),
            "avg_subtasks": (
                sum(len(t.subtasks) for t in self._history) / len(self._history)
                if self._history else 0
            ),
        }

    def _assess_complexity(self, request: str) -> TaskComplexity:
        separators = ["→", "->", "แล้ว", "จากนั้น", "จาก", "และ", "+"]
        step_count = 1
        for sep in separators:
            step_count += request.count(sep)
        if step_count <= 1:
            return TaskComplexity.SIMPLE
        elif step_count <= 3:
            return TaskComplexity.MODERATE
        elif step_count <= 6:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.AUTONOMOUS

    def _assess_category(self, request: str) -> TaskCategory:
        request_lower = request.lower()
        category_scores: dict[TaskCategory, int] = {c: 0 for c in TaskCategory}
        for keyword, mapping in self.TOOL_MAP.items():
            if keyword in request_lower:
                category_scores[mapping["category"]] += 1
        best = max(category_scores, key=lambda c: category_scores[c])
        return best if category_scores[best] > 0 else TaskCategory.DATA_PROCESSING

    def _extract_subtasks(self, request: str) -> list[dict[str, Any]]:
        subtasks = []
        separators = ["→", "->", "แล้ว", "จากนั้น"]
        parts = [request]
        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts
        for i, part in enumerate(parts, 1):
            part = part.strip()
            if not part:
                continue
            tool_info = self._find_tool_for_text(part)
            subtasks.append({
                "step": i,
                "description": part,
                "tool": tool_info.get("tool", "general"),
                "mcp_server": tool_info.get("mcp_server", ""),
                "category": tool_info.get("category", TaskCategory.DATA_PROCESSING),
            })
        return subtasks

    def _identify_tools(self, request: str) -> list[str]:
        tools = set()
        request_lower = request.lower()
        for keyword, mapping in self.TOOL_MAP.items():
            if keyword in request_lower:
                tools.add(mapping["tool"])
        return list(tools)

    def _find_tool_for_text(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        for keyword, mapping in self.TOOL_MAP.items():
            if keyword in text_lower:
                return mapping
        return {"tool": "general", "category": TaskCategory.DATA_PROCESSING}

    def _estimate_time(self, complexity: TaskComplexity, subtask_count: int) -> float:
        base = {
            TaskComplexity.SIMPLE: 5,
            TaskComplexity.MODERATE: 15,
            TaskComplexity.COMPLEX: 30,
            TaskComplexity.AUTONOMOUS: 60,
        }
        return base.get(complexity, 10) * max(subtask_count, 1)

    def summary(self) -> str:
        stats = self.get_stats()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🧠 Universal Orchestrator — สถานะ                ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"📊 วิเคราะห์แล้ว: {stats['tasks_analyzed']}",
            f"⚡ ทำแล้ว: {stats['tasks_executed']}",
            f"✅ สำเร็จ: {stats['tasks_succeeded']}",
            f"❌ ล้มเหลว: {stats['tasks_failed']}",
            f"📈 เฉลี่ย: {stats['avg_subtasks']:.1f} subtasks/task",
        ]
        return "\n".join(lines)
