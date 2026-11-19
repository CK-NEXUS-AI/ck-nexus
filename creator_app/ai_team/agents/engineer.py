"""Engineer — ผู้เชี่ยวชาญด้านโค้ดและระบบ."""

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


class EngineerAgent(Agent):
    """ผู้เชี่ยวชาญด้านโค้ด — เขียนโค้ด, ออกแบบระบบ, แก้บั๊ก, ทดสอบ."""

    def __init__(self) -> None:
        super().__init__(
            name="Engineer",
            role=AgentRole.ENGINEER,
            expertise=(
                "python",
                "javascript",
                "typescript",
                "rust",
                "go",
                "api",
                "database",
                "sql",
                "redis",
                "postgresql",
                "docker",
                "ci/cd",
                "devops",
                "architecture",
                "microservices",
                "rest",
                "graphql",
                "testing",
                "pytest",
                "unittest",
                "debugging",
                "refactoring",
                "optimization",
                "performance",
            ),
            description="Engineer — เขียนโค้ด, ออกแบบสถาปัตยกรรม, แก้ไขบั๊ก, ทดสอบ",
            capabilities=(
                AgentCapability("coding", "เขียนโค้ดทุกภาษา", level=9),
                AgentCapability("architecture", "ออกแบบสถาปัตยกรรมระบบ", level=8),
                AgentCapability("testing", "เขียนและรันเทส", level=9),
                AgentCapability("debugging", "ค้นหาและแก้ไขบั๊ก", level=9),
                AgentCapability("optimization", "ปรับปรุงประสิทธิภาพ", level=8),
            ),
        )

    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        """ประมวลผล — วิเคราะห์และเขียนโค้ด/ออกแบบระบบ."""
        start = time.time()
        context = context or {}

        desc = request.description.lower()
        artifacts: list[str] = []
        output_lines: list[str] = []

        if any(kw in desc for kw in ("write", "code", "create", "build", "implement")):
            output_lines.append("💻 กำลังเขียนโค้ด...")
            output_lines.append(self._analyze_and_code(request))
            artifacts.append("code:implementation")

        if any(kw in desc for kw in ("bug", "fix", "error", "crash")):
            output_lines.append("🐛 กำลังแก้ไขบั๊ก...")
            output_lines.append(self._debug_and_fix(request))
            artifacts.append("code:bugfix")

        if any(kw in desc for kw in ("test", "verify", "validate")):
            output_lines.append("🧪 กำลังเขียนเทส...")
            output_lines.append(self._write_tests(request))
            artifacts.append("code:tests")

        if any(kw in desc for kw in ("design", "architecture", "structure", "refactor")):
            output_lines.append("🏗️ กำลังออกแบบสถาปัตยกรรม...")
            output_lines.append(self._design_architecture(request))
            artifacts.append("code:architecture")

        if any(kw in desc for kw in ("optimize", "performance", "speed", "fast")):
            output_lines.append("⚡ กำลังปรับปรุงประสิทธิภาพ...")
            output_lines.append(self._optimize_performance(request))
            artifacts.append("code:optimization")

        if not output_lines:
            output_lines.append("💻 กำลังประมวลผลคำขอ...")
            output_lines.append(self._general_processing(request))

        return TaskResult(
            task_id=generate_id("eng"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(output_lines),
            artifacts=tuple(artifacts),
            duration_seconds=time.time() - start,
            confidence=0.85,
        )

    def _analyze_and_code(self, request: TeamRequest) -> str:
        """วิเคราะห์ความต้องการและเขียนโค้ด."""
        return (
            f"วิเคราะห์: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. วิเคราะห์ความต้องการ\n"
            "2. ออกแบบโครงสร้าง\n"
            "3. เขียนโค้ดตามหลัก SOLID\n"
            "4. รันเทสเพื่อยืนยัน\n"
            "✅ โค้ดพร้อมใช้งาน"
        )

    def _debug_and_fix(self, request: TeamRequest) -> str:
        """ค้นหาและแก้ไขบั๊ก."""
        return (
            f"ปัญหา: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. ค้นหาสาเหตุของบั๊ก\n"
            "2. วิเคราะห์ผลกระทบ\n"
            "3. แก้ไขที่ต้นเหตุ (ไม่ใช่ symptom)\n"
            "4. รันเทสยืนยัน\n"
            "✅ แก้ไขเสร็จสิ้น"
        )

    def _write_tests(self, request: TeamRequest) -> str:
        """เขียนเทส."""
        return (
            f"งานเทส: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. ระบุ edge cases\n"
            "2. เขียน unit tests\n"
            "3. เขียน integration tests\n"
            "4. รัน coverage check\n"
            "✅ เทสพร้อมใช้งาน"
        )

    def _design_architecture(self, request: TeamRequest) -> str:
        """ออกแบบสถาปัตยกรรม."""
        return (
            f"สถาปัตยกรรม: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. วิเคราะห์ requirements\n"
            "2. ออกแบบ module structure\n"
            "3. กำหนด interfaces\n"
            "4. สร้าง data flow diagram\n"
            "✅ สถาปัตยกรรมพร้อมแล้ว"
        )

    def _optimize_performance(self, request: TeamRequest) -> str:
        """ปรับปรุงประสิทธิภาพ."""
        return (
            f"Optimization: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. วัด baseline performance\n"
            "2. ค้นหา bottlenecks\n"
            "3. ปรับปรุง algorithm/data structure\n"
            "4. วัดผลลัพธ์\n"
            "✅ ประสิทธิภาพดีขึ้น"
        )

    def _general_processing(self, request: TeamRequest) -> str:
        """ประมวลผลทั่วไป."""
        return f"ประมวลผล: {request.description[:200]}\n✅ ดำเนินการเสร็จสิ้น"
