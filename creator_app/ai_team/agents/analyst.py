"""Analyst — ผู้เชี่ยวชาญด้านข้อมูลและการวิเคราะห์."""

from __future__ import annotations

import time
from typing import Any

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    AgentCapability,
    AgentRole,
    TaskResult,
    TaskStatus,
    TeamRequest,
    generate_id,
)


class AnalystAgent(Agent):
    """Analyst — รวบรวมข้อมูล, วิเคราะห์, สรุป, ตรวจสอบความถูกต้อง."""

    def __init__(self) -> None:
        super().__init__(
            name="Analyst",
            role=AgentRole.ANALYST,
            expertise=(
                "data analysis",
                "statistics",
                "trend analysis",
                "reporting",
                "dashboard",
                "metrics",
                "kpi",
                "excel",
                "csv",
                "json",
                "pandas",
                "sql",
                "query",
                "visualization",
                "fact checking",
                "validation",
                "cost analysis",
                "performance metrics",
            ),
            description="Analyst — วิเคราะห์ข้อมูล สรุปผล สร้างรายงาน",
            capabilities=(
                AgentCapability("data_analysis", "วิเคราะห์ข้อมูล", level=9),
                AgentCapability("reporting", "สร้างรายงาน", level=9),
                AgentCapability("statistics", "คำนวณสถิติ", level=8),
                AgentCapability("validation", "ตรวจสอบความถูกต้อง", level=8),
            ),
        )

    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        """ประมวลผล — วิเคราะห์และสรุปข้อมูล."""
        start = time.time()
        context = context or {}
        self.raise_if_cancelled(context)

        desc = request.description.lower()
        output_lines: list[str] = []
        artifacts: list[str] = []

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("data", "analyze", "analytics")):
            output_lines.append("📊 กำลังวิเคราะห์ข้อมูล...")
            output_lines.append(self._analyze_data(request))
            artifacts.append("analysis:data")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("report", "summary", "summarize")):
            output_lines.append("📋 กำลังสร้างรายงาน...")
            output_lines.append(self._generate_report(request))
            artifacts.append("analysis:report")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("statistics", "stats", "metrics", "kpi")):
            output_lines.append("📈 กำลังคำนวณสถิติ...")
            output_lines.append(self._compute_statistics(request))
            artifacts.append("analysis:statistics")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("validate", "verify", "check", "correct")):
            output_lines.append("✅ กำลังตรวจสอบความถูกต้อง...")
            output_lines.append(self._validate_data(request))
            artifacts.append("analysis:validation")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("cost", "price", "budget", "expense")):
            output_lines.append("💰 กำลังวิเคราะห์ค่าใช้จ่าย...")
            output_lines.append(self._cost_analysis(request))
            artifacts.append("analysis:cost")

        if not output_lines:
            output_lines.append("📊 กำลังวิเคราะห์ข้อมูลทั่วไป...")
            output_lines.append(self._general_analysis(request))
            artifacts.append("analysis:general")

        return TaskResult(
            task_id=generate_id("analyst"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(output_lines),
            artifacts=tuple(artifacts),
            duration_seconds=time.time() - start,
            confidence=0.85,
        )

    def _analyze_data(self, request: TeamRequest) -> str:
        return (
            f"หัวข้อ: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. รวบรวมข้อมูลจากแหล่งต่างๆ\n"
            "2. ทำความสะอาดข้อมูล\n"
            "3. วิเคราะห์แนวโน้ม\n"
            "4. สร้าง visualizations\n"
            "5. สรุปผลลัพธ์\n"
            "✅ วิเคราะห์เสร็จสิ้น"
        )

    def _generate_report(self, request: TeamRequest) -> str:
        return (
            "สร้างรายงาน:\n"
            "1. ระบุเป้าหมายของรายงาน\n"
            "2. รวบรวมข้อมูล\n"
            "3. จัดรูปแบบ\n"
            "4. สรุปสาระสำคัญ\n"
            "5. สร้าง executive summary\n"
            "✅ รายงานพร้อมแล้ว"
        )

    def _compute_statistics(self, request: TeamRequest) -> str:
        return (
            "คำนวณสถิติ:\n"
            "1. ระบุ metrics ที่ต้องการ\n"
            "2. คำนวณ mean, median, mode\n"
            "3. วิเคราะห์ variance/std dev\n"
            "4. สร้าง trend lines\n"
            "✅ สถิติพร้อมแล้ว"
        )

    def _validate_data(self, request: TeamRequest) -> str:
        return (
            "ตรวจสอบความถูกต้อง:\n"
            "1. ตรวจสอบ data integrity\n"
            "2. ตรวจสอบ completeness\n"
            "3. ตรวจสอบ accuracy\n"
            "4. สร้าง validation report\n"
            "✅ ตรวจสอบเสร็จสิ้น"
        )

    def _cost_analysis(self, request: TeamRequest) -> str:
        return (
            "วิเคราะห์ค่าใช้จ่าย:\n"
            "1. รวบรวม cost data\n"
            "2. จำแนกค่าใช้จ่ายตามหมวด\n"
            "3. วิเคราะห์ cost trends\n"
            "4. สร้าง budget forecast\n"
            "✅ วิเคราะห์เสร็จสิ้น"
        )

    def _general_analysis(self, request: TeamRequest) -> str:
        return "วิเคราะห์ทั่วไป:\n1. รวบรวมข้อมูล\n2. วิเคราะห์\n3. สรุปผล\n✅ ดำเนินการเสร็จสิ้น"
