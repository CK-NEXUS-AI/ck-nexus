"""Skill Discovery — ค้นหาและติดตั้งสกิลใหม่อัตโนมัติ.

ให้ AI Agent สามารถ:
1. ค้นหาสกิลจาก OpenClaw Skills Directory (5,798+ สกิล)
2. ติดตั้งสกิลใหม่โดยอัตโนมัติ
3. จัดการสกิลที่มีอยู่ (เปิด/ปิด/ลบ)
4. แนะนำสกิลที่เหมาะกับงาน
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SkillStatus(str, Enum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class SkillInfo:
    name: str
    description: str
    category: str
    source: str = ""
    status: SkillStatus = SkillStatus.AVAILABLE
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    tools_provided: list[str] = field(default_factory=list)
    install_command: str = ""
    installed_at: float | None = None


class SkillDiscovery:
    """ค้นหาและจัดการสกิลอัตโนมัติ.

    วิธีใช้:
        discovery = SkillDiscovery()
        discovery.index_directory()

        # ค้นหาสกิล
        skills = discovery.search("email automation")

        # ติดตั้ง
        discovery.install("gmail-headless")

        # แนะนำสกิลสำหรับงาน
        recommended = discovery.recommend_for_task("อ่านอีเมล → ดึง OTP → ยืนยัน")
    """

    BUILTIN_SKILLS: list[SkillInfo] = [
        SkillInfo(
            name="gmail-headless",
            description="Gmail headless access — อ่าน/ส่งอีเมลไม่ต้องเบราว์เซอร์",
            category="email",
            tools_provided=["read_inbox", "send_email", "wait_for_otp"],
            tags=["email", "otp", "headless"],
        ),
        SkillInfo(
            name="captcha-solver",
            description="CAPTCHA solver — แก้ reCAPTCHA, hCaptcha, Turnstile อัตโนมัติ",
            category="automation",
            tools_provided=["solve_recaptcha", "solve_hcaptcha", "solve_turnstile"],
            tags=["captcha", "automation", "signup"],
        ),
        SkillInfo(
            name="temp-email",
            description="Temporary email — สร้างอีเมลชั่วคราว + ดึง OTP อัตโนมัติ",
            category="email",
            tools_provided=["create_temp_email", "read_temp_inbox", "extract_otp"],
            tags=["email", "otp", "temp"],
        ),
        SkillInfo(
            name="web-scraper",
            description="Web scraping — ดึงข้อมูลจากเว็บ + anti-bot bypass",
            category="scraping",
            tools_provided=["scrape_url", "extract_text", "screenshot"],
            tags=["scraping", "web", "data"],
        ),
        SkillInfo(
            name="anti-detect-browser",
            description="Anti-detect browser — fingerprint spoofing + 170+ profiles",
            category="browser",
            tools_provided=["launch_profile", "rotate_fingerprint", "stealth_navigate"],
            tags=["browser", "stealth", "fingerprint"],
        ),
        SkillInfo(
            name="hitl-gate",
            description="Human-in-the-loop — หยุดรอ approve ก่อนทำ action สำคัญ",
            category="security",
            tools_provided=["request_approval", "check_policy", "audit_log"],
            tags=["security", "approval", "hitl"],
        ),
        SkillInfo(
            name="reflexion",
            description="Self-learning — สะท้อนคิดและเรียนรู้จากความผิดพลาด",
            category="intelligence",
            tools_provided=["reflect", "analyze_pattern", "get_feedback"],
            tags=["intelligence", "learning", "self-improvement"],
        ),
        SkillInfo(
            name="mcp-hub",
            description="MCP Hub — เชื่อมต่อทุกแอพผ่าน Model Context Protocol",
            category="integration",
            tools_provided=["call_mcp_tool", "list_mcp_servers", "health_check"],
            tags=["mcp", "integration", "hub"],
        ),
        SkillInfo(
            name="computer-use",
            description="Computer Use — ควบคุม GUI เหมือนมนุษย์",
            category="automation",
            tools_provided=["click", "type", "screenshot", "scroll"],
            tags=["gui", "automation", "computer_use"],
        ),
        SkillInfo(
            name="background-executor",
            description="Background execution — ทำงานเบื้องหลังแบบ fire-and-forget",
            category="automation",
            tools_provided=["submit_task", "schedule", "check_status"],
            tags=["background", "scheduling", "async"],
        ),
        SkillInfo(
            name="multi-agent-orchestrator",
            description="Multi-agent — จัดทีม AI หลายตัว แบ่งงาน + รวมผล",
            category="intelligence",
            tools_provided=["assign_role", "coordinate", "merge_results"],
            tags=["multi_agent", "orchestration", "team"],
        ),
        SkillInfo(
            name="telegram-bridge",
            description="Telegram Bot — ส่ง/รับข้อความ แจ้งเตือนผ่าน Telegram",
            category="communication",
            tools_provided=["send_message", "send_photo", "receive_update"],
            tags=["telegram", "notification", "bot"],
        ),
    ]

    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._install_log: list[dict[str, Any]] = []
        for skill in self.BUILTIN_SKILLS:
            self._skills[skill.name] = skill

    def index_directory(self) -> int:
        """ทำ index สกิลทั้งหมด."""
        # ในระบบจริงจะเชื่อม OpenClaw Skills Directory
        return len(self._skills)

    def search(self, query: str, limit: int = 10) -> list[SkillInfo]:
        """ค้นหาสกิล."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            score = 0
            if query_lower in skill.name.lower():
                score += 10
            if query_lower in skill.description.lower():
                score += 5
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 3
            if score > 0:
                results.append((score, skill))
        results.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in results[:limit]]

    def recommend_for_task(self, task_description: str) -> list[SkillInfo]:
        """แนะนำสกิลสำหรับงานหนึ่ง."""
        keywords = {
            "อีเมล": "email",
            "gmail": "email",
            "otp": "email",
            "เว็บ": "scraping",
            "scrape": "scraping",
            "สมัคร": "automation",
            "signup": "automation",
            "captcha": "automation",
            "approve": "security",
            "อนุมัติ": "security",
            "gui": "automation",
            "หน้าจอ": "automation",
            "telegram": "communication",
            "slack": "communication",
            "schedule": "automation",
            "เบื้องหลัง": "automation",
            "เรียนรู้": "intelligence",
            "learn": "intelligence",
        }
        task_lower = task_description.lower()
        matched_categories = set()
        for kw, cat in keywords.items():
            if kw in task_lower:
                matched_categories.add(cat)

        recommended = []
        for skill in self._skills.values():
            if skill.category in matched_categories:
                recommended.append(skill)
        return recommended

    def install(self, skill_name: str) -> bool:
        """ติดตั้งสกิล."""
        skill = self._skills.get(skill_name)
        if not skill:
            return False
        skill.status = SkillStatus.INSTALLED
        skill.installed_at = time.time()
        self._install_log.append({
            "skill": skill_name,
            "action": "install",
            "timestamp": time.time(),
        })
        return True

    def uninstall(self, skill_name: str) -> bool:
        """ลบสกิล."""
        skill = self._skills.get(skill_name)
        if not skill:
            return False
        skill.status = SkillStatus.AVAILABLE
        skill.installed_at = None
        self._install_log.append({
            "skill": skill_name,
            "action": "uninstall",
            "timestamp": time.time(),
        })
        return True

    def get_installed(self) -> list[SkillInfo]:
        """ดึงสกิลที่ติดตั้งแล้ว."""
        return [s for s in self._skills.values() if s.status in (SkillStatus.INSTALLED, SkillStatus.ACTIVE)]

    def get_all(self) -> list[SkillInfo]:
        """ดึงสกิลทั้งหมด."""
        return list(self._skills.values())

    def get_stats(self) -> dict[str, Any]:
        """ดูสถิติ."""
        all_skills = list(self._skills.values())
        return {
            "total": len(all_skills),
            "installed": sum(1 for s in all_skills if s.status == SkillStatus.INSTALLED),
            "active": sum(1 for s in all_skills if s.status == SkillStatus.ACTIVE),
            "available": sum(1 for s in all_skills if s.status == SkillStatus.AVAILABLE),
            "categories": list(set(s.category for s in all_skills)),
        }

    def summary(self) -> str:
        stats = self.get_stats()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🧩 Skill Discovery — สถานะ                       ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"📊 สกิลทั้งหมด: {stats['total']}",
            f"✅ ติดตั้งแล้ว: {stats['installed']}",
            f"🟢 ใช้งานอยู่: {stats['active']}",
            f"📦 พร้อมใช้: {stats['available']}",
            f"📂 หมวดหมู่: {', '.join(stats['categories'])}",
            "",
        ]
        for cat in sorted(stats["categories"]):
            skills = [s for s in self._skills.values() if s.category == cat]
            lines.append(f"📂 {cat.upper()}")
            for s in skills:
                status_emoji = {"installed": "✅", "active": "🟢", "available": "📦"}.get(s.status.value, "❓")
                lines.append(f"  {status_emoji} {s.name} — {s.description[:60]}")
            lines.append("")
        return "\n".join(lines)
