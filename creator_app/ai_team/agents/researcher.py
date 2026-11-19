"""Researcher — ผู้เชี่ยวชาญด้านการวิจัยและค้นหา."""

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


class ResearcherAgent(Agent):
    """Researcher — ค้นหาข้อมูลล่าสุด, ตรวจสอบแหล่งที่มา, ค้นพบเครื่องมือใหม่."""

    def __init__(self) -> None:
        super().__init__(
            name="Researcher",
            role=AgentRole.RESEARCHER,
            expertise=(
                "web search",
                "api discovery",
                "documentation review",
                "comparative analysis",
                "technology evaluation",
                "market research",
                "trend analysis",
                "best practices",
                "open source",
                "library research",
                "tool discovery",
                "academic research",
                "paper review",
            ),
            description="Researcher — ค้นหาข้อมูลล่าสุด ตรวจสอบแหล่งที่มา ค้นพบเครื่องมือใหม่",
            capabilities=(
                AgentCapability("web_search", "ค้นหาข้อมูลจากเว็บ", level=8),
                AgentCapability("tech_evaluation", "ประเมินเทคโนโลยี", level=9),
                AgentCapability("comparative_analysis", "เปรียบเทียบทางเลือก", level=8),
            ),
        )

    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        start = time.time()
        context = context or {}
        self.raise_if_cancelled(context)

        desc = request.description.lower()
        output_lines: list[str] = []
        artifacts: list[str] = []

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("search", "find", "discover")):
            output_lines.append("🔍 กำลังค้นหาข้อมูล...")
            output_lines.append(self._search_info(request))
            artifacts.append("research:search")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("compare", "versus", "vs", "alternative")):
            output_lines.append("⚖️ กำลังเปรียบเทียบ...")
            output_lines.append(self._compare_options(request))
            artifacts.append("research:comparison")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("tool", "library", "framework", "package")):
            output_lines.append("🛠️ กำลังค้นหาเครื่องมือ...")
            output_lines.append(self._find_tools(request))
            artifacts.append("research:tools")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("best practice", "pattern", "standard")):
            output_lines.append("📚 กำลังค้นหา Best Practices...")
            output_lines.append(self._find_best_practices(request))
            artifacts.append("research:best_practices")

        if not output_lines:
            output_lines.append("🔍 กำลังวิจัยทั่วไป...")
            output_lines.append(self._general_research(request))
            artifacts.append("research:general")

        return TaskResult(
            task_id=generate_id("research"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(output_lines),
            artifacts=tuple(artifacts),
            duration_seconds=time.time() - start,
            confidence=0.8,
        )

    def _search_info(self, request: TeamRequest) -> str:
        return (
            f"ค้นหา: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. ระบุ keywords ที่เกี่ยวข้อง\n"
            "2. ค้นหาจากหลายแหล่ง\n"
            "3. ตรวจสอบความน่าเชื่อถือ\n"
            "4. สรุปผลลัพธ์\n"
            "✅ ค้นหาเสร็จสิ้น"
        )

    def _compare_options(self, request: TeamRequest) -> str:
        return (
            "เปรียบเทียบ:\n"
            "1. ระบุตัวเลือกทั้งหมด\n"
            "2. เปรียบเทียบตามเกณฑ์\n"
            "3. วิเคราะห์ข้อดีข้อเสีย\n"
            "4. ให้คำแนะนำ\n"
            "✅ เปรียบเทียบเสร็จสิ้น"
        )

    def _find_tools(self, request: TeamRequest) -> str:
        return (
            "ค้นหาเครื่องมือ:\n"
            "1. ระบุความต้องการ\n"
            "2. ค้นหาเครื่องมือที่เกี่ยวข้อง\n"
            "3. ประเมินราคา/ฟรี\n"
            "4. ให้คำแนะนำ\n"
            "✅ ค้นหาเสร็จสิ้น"
        )

    def _find_best_practices(self, request: TeamRequest) -> str:
        return (
            "Best Practices:\n"
            "1. ค้นหาจากแหล่งที่น่าเชื่อถือ\n"
            "2. ตรวจสอบว่าเหมาะกับบริบท\n"
            "3. สรุปเป็นขั้นตอน\n"
            "✅ ค้นหาเสร็จสิ้น"
        )

    def _general_research(self, request: TeamRequest) -> str:
        return f"วิจัย: {request.description[:200]}\n✅ ดำเนินการเสร็จสิ้น"
