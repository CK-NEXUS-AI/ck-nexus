"""Director — หัวหน้าทีม ผู้ประสานงานและวางแผน."""

from __future__ import annotations

import time
from typing import Any

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    AgentCapability,
    AgentRole,
    PlanStep,
    TaskResult,
    TaskStatus,
    TeamPlan,
    TeamRequest,
    generate_id,
)


def _text_matches(text: str, keyword: str) -> bool:
    """ตรวจสอบว่า keyword ตรงกับข้อความ (ใช้ word-level matching)."""
    if keyword in text:
        return True
    text_words = set(text.lower().split())
    keyword_words = set(keyword.lower().split())
    return bool(text_words & keyword_words)


class DirectorAgent(Agent):
    """หัวหน้าทีม — รับคำสั่ง วางแผน แบ่งงาน ประสานงาน รวมผล."""

    def __init__(self) -> None:
        super().__init__(
            name="Director",
            role=AgentRole.DIRECTOR,
            expertise=(
                "planning",
                "coordination",
                "decision making",
                "conflict resolution",
                "knowledge synthesis",
                "task decomposition",
                "priority management",
                "team orchestration",
                "strategic thinking",
            ),
            description="หัวหน้าทีม — รับคำสั่ง วางแผน แบ่งงาน ประสานงาน รวมผล",
            capabilities=(
                AgentCapability("planning", "วางแผนงานและแบ่งขั้นตอน"),
                AgentCapability("coordination", "ประสานงานระหว่างทีม"),
                AgentCapability("decision_making", "ตัดสินใจและแก้ไขข้อขัดแย้ง"),
                AgentCapability("synthesis", "รวมผลลัพธ์จากทุกคน"),
            ),
        )

    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        start = time.time()
        context = context or {}
        agents = context.get("agents", [])

        available_roles = set()
        for a in agents:
            if hasattr(a, "role"):
                available_roles.add(a.role.value)

        plan = self._create_plan(request, available_roles)

        summary_lines = [
            f"📋 แผนงาน: {request.description[:100]}",
            f"📊 จำนวนขั้นตอน: {plan.total_steps}",
            f"👥 ทีมที่เกี่ยวข้อง: {', '.join(s.agent_role for s in plan.steps)}",
            f"⏱️ เวลาโดยประมาณ: {plan.estimated_duration:.0f} วินาที",
        ]

        return TaskResult(
            task_id=generate_id("dir"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(summary_lines),
            artifacts=(f"plan:{request.request_id}",),
            duration_seconds=time.time() - start,
            confidence=0.9,
            metadata={"plan": plan, "priority": request.priority.value},
        )

    def synthesize_results(
        self, step_results: list[TaskResult], request: TeamRequest
    ) -> TaskResult:
        outputs: list[str] = []
        all_artifacts: list[str] = []
        total_confidence = 0.0
        members_used: list[str] = []

        for result in step_results:
            if result.status == TaskStatus.COMPLETED:
                outputs.append(f"[{result.agent_name}] {result.output}")
                all_artifacts.extend(result.artifacts)
                total_confidence += result.confidence
                if result.agent_name not in members_used:
                    members_used.append(result.agent_name)

        avg_confidence = total_confidence / len(step_results) if step_results else 0.0
        final_output = f"✅ ผลลัพธ์จากทีม: {request.description[:100]}\n\n" + "\n\n".join(outputs)

        return TaskResult(
            task_id=generate_id("dir-synth"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output=final_output,
            artifacts=tuple(all_artifacts),
            confidence=avg_confidence,
            metadata={"members_used": members_used},
        )

    def _create_plan(self, request: TeamRequest, available_roles: set[str]) -> TeamPlan:
        steps: list[PlanStep] = []
        desc = request.description.lower()
        step_counter = 0

        # (keywords_list, role, description)
        keyword_groups: list[tuple[list[str], str, str]] = [
            (["code", "เขียนโค้ด", "โค้ด", "coding"], "engineer", "เขียน/แก้ไขโค้ด"),
            (["create", "สร้าง", "build", "implement"], "engineer", "สร้างระบบ"),
            (["bug", "fix", "แก้ไข", "error", "crash"], "engineer", "แก้ไขปัญหา"),
            (["test", "เทส", "verify", "validate"], "engineer", "เขียน/รันเทส"),
            (["deploy", "ติดตั้ง", "install"], "engineer", "ติดตั้งระบบ"),
            (["architecture", "สถาปัตยกรรม", "refactor"], "engineer", "ออกแบบสถาปัตยกรรม"),
            (["performance", "ประสิทธิภาพ", "optimize"], "engineer", "ปรับปรุงประสิทธิภาพ"),
            (["security", "ความปลอดภัย"], "guardian", "ตรวจสอบความปลอดภัย"),
            (["credential", "คีย์", "key", "token", "password"], "guardian", "จัดการคีย์/ความลับ"),
            (["secret", "ลับ", "ความลับ"], "guardian", "ตรวจสอบข้อมูลลับ"),
            (["auth", "permission", "สิทธิ์", "ยืนยัน"], "guardian", "ตรวจสอบสิทธิ์"),
            (["audit", "ตรวจ"], "guardian", "ตรวจสอบ"),
            (["data", "ข้อมูล"], "analyst", "วิเคราะห์ข้อมูล"),
            (["report", "รายงาน"], "analyst", "สร้างรายงาน"),
            (["summary", "summarize", "สรุป", "สรุปผล"], "analyst", "สรุปผล"),
            (["statistics", "stats", "สถิติ"], "analyst", "คำนวณสถิติ"),
            (["analytics", "วิเคราะห์"], "analyst", "วิเคราะห์"),
            (["search", "ค้นหา", "find", "ค้น"], "researcher", "ค้นหาข้อมูล"),
            (["research", "วิจัย", "ค้นคว้า"], "researcher", "วิจัยและค้นคว้า"),
            (["compare", "versus", "vs", "เปรียบเทียบ"], "researcher", "เปรียบเทียบ"),
            (["tool", "เครื่องมือ", "library", "framework"], "researcher", "ค้นหาเครื่องมือ"),
            (["design", "ออกแบบ"], "designer", "ออกแบบ UI/UX"),
            (["ui", "อินเทอร์เฟซ", "interface"], "designer", "ออกแบบอินเทอร์เฟซ"),
            (["ux", "experience", "ประสบการณ์"], "designer", "ปรับปรุงประสบการณ์ผู้ใช้"),
            (["style", "สี", "color", "theme", "ฟอนต์"], "designer", "จัดรูปแบบ"),
            (["connect", "เชื่อมต่อ", "integration"], "connector", "เชื่อมต่อระบบ"),
            (["api", "rest", "graphql", "endpoint"], "connector", "สร้าง/เชื่อม API"),
            (["gmail", "อีเมล", "email", "mail"], "connector", "เชื่อม Gmail"),
            (["telegram", "bot", "messaging"], "connector", "เชื่อม Telegram"),
            (["webhook", "event"], "connector", "ตั้งค่า Webhook"),
        ]

        assigned_roles: set[str] = set()
        for keywords, role, description in keyword_groups:
            if role not in available_roles or role in assigned_roles:
                continue
            if any(_text_matches(desc, kw) for kw in keywords):
                step_counter += 1
                steps.append(
                    PlanStep(
                        step_id=f"step-{step_counter:03d}",
                        agent_name=role.title(),
                        agent_role=role,
                        description=description,
                        priority=request.priority,
                    )
                )
                assigned_roles.add(role)

        if not steps and "engineer" in available_roles:
            steps.append(
                PlanStep(
                    step_id="step-001",
                    agent_name="Engineer",
                    agent_role="engineer",
                    description="ประมวลผลคำขอทั่วไป",
                    priority=request.priority,
                )
            )

        return TeamPlan(
            request_id=request.request_id,
            steps=steps,
            total_steps=len(steps),
            estimated_duration=len(steps) * 10.0,
        )
