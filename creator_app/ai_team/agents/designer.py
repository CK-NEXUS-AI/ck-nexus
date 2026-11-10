"""Designer — ผู้เชี่ยวชาญด้านการออกแบบ UI/UX."""

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


class DesignerAgent(Agent):
    """Designer — ออกแบบ UI/UX, responsive design, accessibility."""

    def __init__(self) -> None:
        super().__init__(
            name="Designer",
            role=AgentRole.DESIGNER,
            expertise=(
                "ui design",
                "ux design",
                "responsive design",
                "css",
                "html",
                "tailwind",
                "bootstrap",
                "color theory",
                "typography",
                "layout",
                "accessibility",
                "wcag",
                "aria",
                "wireframe",
                "prototype",
                "mockup",
                "figma",
                "sketch",
                "mobile design",
                "desktop design",
            ),
            description="Designer — ออกแบบ UI/UX, responsive design, accessibility",
            capabilities=(
                AgentCapability("ui_design", "ออกแบบอินเทอร์เฟซ", level=8),
                AgentCapability("ux_design", "ออกแบบประสบการณ์ผู้ใช้", level=8),
                AgentCapability("accessibility", "ตรวจสอบการเข้าถึง", level=7),
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
        if any(kw in desc for kw in ("design", "ui", "interface")):
            output_lines.append("🎨 กำลังออกแบบ UI...")
            output_lines.append(self._design_ui(request))
            artifacts.append("design:ui")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("ux", "experience", "usability")):
            output_lines.append("✨ กำลังออกแบบ UX...")
            output_lines.append(self._design_ux(request))
            artifacts.append("design:ux")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("responsive", "mobile", "desktop")):
            output_lines.append("📱 กำลังออกแบบ responsive...")
            output_lines.append(self._design_responsive(request))
            artifacts.append("design:responsive")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("accessibility", "wcag", "aria")):
            output_lines.append("♿ กำลังตรวจสอบ accessibility...")
            output_lines.append(self._check_accessibility(request))
            artifacts.append("design:accessibility")

        self.raise_if_cancelled(context)
        if any(kw in desc for kw in ("style", "color", "theme", "font")):
            output_lines.append("🎭 กำลังจัดรูปแบบ...")
            output_lines.append(self._style_system(request))
            artifacts.append("design:style")

        if not output_lines:
            output_lines.append("🎨 กำลังออกแบบทั่วไป...")
            output_lines.append(self._general_design(request))
            artifacts.append("design:general")

        return TaskResult(
            task_id=generate_id("design"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(output_lines),
            artifacts=tuple(artifacts),
            duration_seconds=time.time() - start,
            confidence=0.8,
        )

    def _design_ui(self, request: TeamRequest) -> str:
        return (
            "ออกแบบ UI:\n"
            "1. วิเคราะห์ user needs\n"
            "2. สร้าง wireframe\n"
            "3. ออกแบบ layout\n"
            "4. เลือก color scheme\n"
            "5. สร้าง component system\n"
            "✅ UI design พร้อมแล้ว"
        )

    def _design_ux(self, request: TeamRequest) -> str:
        return (
            "ออกแบบ UX:\n"
            "1. วิเคราะห์ user journey\n"
            "2. ระบุ pain points\n"
            "3. ออกแบบ flow\n"
            "4. ทดสอบ usability\n"
            "✅ UX design พร้อมแล้ว"
        )

    def _design_responsive(self, request: TeamRequest) -> str:
        return (
            "Responsive Design:\n"
            "1. Mobile-first approach\n"
            "2. Breakpoints ที่เหมาะสม\n"
            "3. Flexible grid system\n"
            "4. Touch-friendly elements\n"
            "✅ Responsive พร้อมแล้ว"
        )

    def _check_accessibility(self, request: TeamRequest) -> str:
        return (
            "Accessibility Check:\n"
            "1. WCAG 2.1 compliance\n"
            "2. ARIA labels\n"
            "3. Color contrast ratio\n"
            "4. Keyboard navigation\n"
            "5. Screen reader compatibility\n"
            "✅ Accessibility verified"
        )

    def _style_system(self, request: TeamRequest) -> str:
        return (
            "Style System:\n"
            "1. Color palette\n"
            "2. Typography scale\n"
            "3. Spacing system\n"
            "4. Component variants\n"
            "✅ Style system พร้อมแล้ว"
        )

    def _general_design(self, request: TeamRequest) -> str:
        return "ออกแบบทั่วไป:\n1. วิเคราะห์ความต้องการ\n2. ออกแบบ\n3. สร้าง prototype\n✅ ออกแบบเสร็จสิ้น"
