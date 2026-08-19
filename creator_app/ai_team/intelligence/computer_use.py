"""Computer Use — ควบคุม GUI เหมือนมนุษย์.

ใช้โมเดล AI ที่รองรับ Computer Use (Gemini 2.5, Claude Computer Use)
เพื่อ:
1. ดูหน้าจอ → วิเคราะห์สิ่งที่เห็น
2. จำลองการคลิก/พิมพ์/ลาก → ทำงานบน GUI
3. ทำซ้ำจนกว่าจะเสร็จ → ไม่ต้องมีมนุษย์คุม

ใช้ได้กับ:
- เว็บฟอร์มที่ไม่มี API
- แอพที่ไม่มี API
- การกรอกข้อมูลอัตโนมัติ
- การทำงานข้ามแอพ
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    """ประเภทของการกระทำบน GUI."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    DRAG = "drag"
    HOVER = "hover"
    SCREENSHOT = "screenshot"
    WAIT = "wait"


@dataclass
class ScreenElement:
    """องค์ประกอบบนหน้าจอ."""
    element_id: str
    label: str
    element_type: str  # button, text_field, link, image, etc.
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)  # x1, y1, x2, y2
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GUIAction:
    """การกระทำหนึ่งครั้งบน GUI."""
    action_type: ActionType
    target: str | None = None
    text: str | None = None
    key: str | None = None
    coordinates: tuple[int, int] | None = None
    scroll_direction: str = "down"
    scroll_amount: int = 3
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class TaskStep:
    """ขั้นตอนหนึ่งของงาน."""
    step_id: int
    description: str
    action: GUIAction
    expected_result: str = ""
    status: str = "pending"  # pending, executing, success, failed
    error: str = ""


class ComputerUseAgent:
    """Agent ที่ควบคุม GUI ได้เหมือนมนุษย์.

    วิธีใช้:
        agent = ComputerUseAgent()

        # สร้าง plan จากคำสั่ง
        steps = agent.plan(
            "สมัครสมาชิกเว็บ example.com",
            screen_elements=[
                ScreenElement("btn-signup", "Sign Up", "button", (100, 200, 300, 250)),
                ScreenElement("input-email", "Email", "text_field", (100, 300, 400, 340)),
                ScreenElement("input-pass", "Password", "text_field", (100, 350, 400, 390)),
            ]
        )

        #  executes steps
        for step in steps:
            result = agent.execute_step(step)
            if not result["success"]:
                agent.revise_plan(step, result["error"])
    """

    def __init__(self) -> None:
        self._action_history: list[dict[str, Any]] = []
        self._current_plan: list[TaskStep] = []
        self._retry_count = 0
        self._max_retries = 3

    def plan(
        self,
        task_description: str,
        screen_elements: list[ScreenElement] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[TaskStep]:
        """สร้างแผนงานจากคำอธิบาย."""
        # วิเคราะห์ task → สร้าง steps
        steps = self._analyze_task(task_description, screen_elements or [], context or {})
        self._current_plan = steps
        self._retry_count = 0
        return steps

    def execute_step(self, step: TaskStep) -> dict[str, Any]:
        """Execute a single step on the GUI."""
        step.status = "executing"

        # จำลองการ execute (ในระบบจริงจะเชื่อม Playwright/Shizuku)
        result = self._simulate_action(step.action)

        step.status = "success" if result["success"] else "failed"
        if not result["success"]:
            step.error = result.get("error", "Unknown error")

        self._action_history.append({
            "step_id": step.step_id,
            "action": step.action.action_type.value,
            "target": step.action.target,
            "success": result["success"],
            "timestamp": time.time(),
        })

        return result

    def revise_plan(self, failed_step: TaskStep, error: str) -> list[TaskStep]:
        """ปรับปรุงแผนเมื่อขั้นตอนล้มเหลว."""
        self._retry_count += 1

        if self._retry_count > self._max_retries:
            return self._current_plan

        # วิเคราะห์ error → สร้าง steps ใหม่
        revised = self._analyze_error_and_revise(failed_step, error)
        return revised

    def get_status(self) -> dict[str, Any]:
        """ดูสถานะปัจจุบัน."""
        total = len(self._current_plan)
        completed = sum(1 for s in self._current_plan if s.status == "success")
        failed = sum(1 for s in self._current_plan if s.status == "failed")

        return {
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "retry_count": self._retry_count,
            "progress": round(completed / total * 100, 1) if total > 0 else 0,
        }

    def get_action_history(self) -> list[dict[str, Any]]:
        """ดูประวัติการกระทำ."""
        return self._action_history.copy()

    def _analyze_task(
        self,
        description: str,
        elements: list[ScreenElement],
        context: dict[str, Any],
    ) -> list[TaskStep]:
        """วิเคราะห์ task → สร้าง steps (แบบง่าย)."""
        steps = []
        step_id = 1

        # ถ้ามี elements → สร้าง steps จาก element types
        for elem in elements:
            if elem.element_type == "button" and "sign" in elem.label.lower():
                steps.append(TaskStep(
                    step_id=step_id,
                    description=f"คลิกปุ่ม {elem.label}",
                    action=GUIAction(
                        action_type=ActionType.CLICK,
                        target=elem.element_id,
                        coordinates=elem.bbox[:2],
                        reasoning=f"พบปุ่ม {elem.label} → คลิกเพื่อดำเนินการต่อ",
                    ),
                    expected_result="หน้าจอเปลี่ยนไปยังขั้นตอนถัดไป",
                ))
                step_id += 1
            elif elem.element_type == "text_field":
                steps.append(TaskStep(
                    step_id=step_id,
                    description=f"กรอกข้อมูลในช่อง {elem.label}",
                    action=GUIAction(
                        action_type=ActionType.TYPE_TEXT,
                        target=elem.element_id,
                        text=context.get(elem.label.lower(), "test@example.com"),
                        reasoning=f"พบช่อง {elem.label} → กรอกข้อมูลที่จำเป็น",
                    ),
                    expected_result=f"ข้อมูลปรากฏในช่อง {elem.label}",
                ))
                step_id += 1

        # เพิ่ม submit step ถ้ามีปุ่ม submit
        for elem in elements:
            if elem.element_type == "button" and any(
                kw in elem.label.lower() for kw in ("submit", "confirm", "register", "save")
            ):
                steps.append(TaskStep(
                    step_id=step_id,
                    description=f"คลิกปุ่ม {elem.label}",
                    action=GUIAction(
                        action_type=ActionType.CLICK,
                        target=elem.element_id,
                        coordinates=elem.bbox[:2],
                        reasoning=f"ข้อมูลกรอกครบ → คลิก {elem.label}",
                    ),
                    expected_result="ได้รับการยืนยัน",
                ))
                step_id += 1

        if not steps:
            steps.append(TaskStep(
                step_id=1,
                description="ถ่ายภาพหน้าจอเพื่อวิเคราะห์",
                action=GUIAction(
                    action_type=ActionType.SCREENSHOT,
                    reasoning="ไม่พบ elements → ถ่ายภาพก่อน",
                ),
                expected_result="ได้ภาพหน้าจอ",
            ))

        return steps

    def _simulate_action(self, action: GUIAction) -> dict[str, Any]:
        """จำลองการกระทำ (ในระบบจริงจะเชื่อม Playwright/Shizuku)."""
        # สำหรับตอนนี้ return success แบบง่าย
        return {
            "success": True,
            "action": action.action_type.value,
            "target": action.target,
            "timestamp": time.time(),
        }

    def _analyze_error_and_revise(
        self,
        failed_step: TaskStep,
        error: str,
    ) -> list[TaskStep]:
        """วิเคราะห์ error → สร้าง steps ใหม่."""
        revised = []
        for step in self._current_plan:
            if step.step_id == failed_step.step_id:
                # ปรับ action ตาม error type
                new_action = step.action
                if "not found" in error.lower():
                    # ลองค้นหา element ใหม่
                    new_action = GUIAction(
                        action_type=ActionType.SCREENSHOT,
                        reasoning="Element ไม่พบ → ถ่ายภาพใหม่เพื่อค้นหา",
                    )
                elif "timeout" in error.lower():
                    # รอแล้วลองใหม่
                    new_action = GUIAction(
                        action_type=ActionType.WAIT,
                        reasoning="Timeout → รอ 2 วินาทีแล้วลองใหม่",
                    )
                revised.append(TaskStep(
                    step_id=step.step_id,
                    description=f"[Retry] {step.description}",
                    action=new_action,
                    expected_result=step.expected_result,
                ))
            else:
                revised.append(step)
        return revised
