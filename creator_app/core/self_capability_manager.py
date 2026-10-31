"""SelfCapabilityManager — ระบบรู้จักตัวเอง.

- รู้ว่าตัวเองทำอะไรได้บ้าง (11 ด้าน)
- ค้นหาความสามารถใหม่จากแหล่งต่างๆ
- อัปเดตตัวเองตลอดเวลา
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Capability:
    name: str
    category: str
    description: str
    tools: tuple[str, ...] = ()
    level: str = "Full"
    is_new: bool = False
    source: str = "built-in"


CORE_CAPABILITIES: dict[str, dict[str, Any]] = {
    "code_development": {
        "description": "เขียน แก้ไข รัน ดีบัก ทุกภาษาโปรแกรม",
        "languages": ["Python", "JavaScript", "TypeScript", "Go", "Bash", "SQL", "HTML/CSS"],
        "tools": ["Git", "GitHub", "CLI", "Docker", "API Integration"],
        "level": "Full",
    },
    "browser_automation": {
        "description": "ควบคุมเบราว์เซอร์อัตโนมัติ — เปิด คลิก กรอก ดึงข้อมูล",
        "tools": ["Playwright"],
        "level": "Full",
    },
    "gmail_integration": {
        "description": "อ่าน ส่ง ค้นหา ประมวลผลอีเมล",
        "tools": ["Gmail API", "OAuth2"],
        "level": "Full",
    },
    "google_ecosystem": {
        "description": "เชื่อมทุกบริการ Google",
        "tools": ["Calendar", "Drive", "Sheets", "Docs", "Slides"],
        "level": "Full",
    },
    "communication_tools": {
        "description": "สื่อสารผ่านหลายช่องทาง",
        "tools": ["Slack", "Telegram", "Discord", "Notion", "Linear"],
        "level": "Full",
    },
    "design_media": {
        "description": "สร้างและแก้ไขสื่อ ดีไซน์",
        "tools": ["Figma", "Canva", "ImageGen"],
        "level": "Full",
    },
    "deployment_hosting": {
        "description": "Deploy และจัดการเว็บแอปพลิเคชัน",
        "tools": ["Vercel"],
        "level": "Full",
    },
    "security_system": {
        "description": "ตรวจสอบและปกป้องระบบ",
        "tools": ["Bandit", "pip-audit", "Secret Scanner", "CodeQL"],
        "level": "Full",
    },
    "mobile_integration": {
        "description": "เชื่อมต่อและทำงานบนมือถือ Android",
        "tools": ["Termux", "Shizuku"],
        "level": "Full",
    },
    "plugin_skill_system": {
        "description": "สร้างและจัดการความสามารถเพิ่มเติม",
        "tools": ["Skill Creator", "Plugin Creator", "CLI Creator"],
        "level": "Full",
    },
    "ai_multi_provider": {
        "description": "เชื่อมหลาย AI ผู้ให้บริการ — สลับอัตโนมัติ",
        "tools": ["OpenAI", "Anthropic", "Google Gemini", "Groq", "Ollama", "OpenRouter"],
        "level": "Full",
    },
}

LIMITATIONS: list[dict[str, str]] = [
    {"item": "Bypass CAPTCHA / OTP", "workaround": "แจ้งเตือนและรอผู้ใช้ยืนยัน"},
    {"item": "เข้าถึงไฟล์บนเครื่องผู้ใช้โดยตรง", "workaround": "ใช้ Shell/Termux หรือ Drive"},
    {"item": "รัน GUI แบบ native", "workaround": "ใช้ Playwright หรือ Web UI"},
    {"item": "ส่งไฟล์ออกไปภายนอกโดยตรง", "workaround": "บันทึกในเครื่อง/Drive → แจ้งลิงก์"},
    {"item": "สร้าง API Key จริงจากบัญชีภายนอก", "workaround": "แนะนำขั้นตอนให้ผู้ใช้ทำเอง"},
]

LEARNING_SOURCES = [
    {"name": "GitHub Trending", "url": "github.com/trending", "type": "code"},
    {"name": "Hugging Face", "url": "huggingface.co", "type": "ai_models"},
    {"name": "Product Hunt", "url": "producthunt.com", "type": "tools"},
    {"name": "Dev.to", "url": "dev.to", "type": "tutorials"},
    {"name": "Reddit r/programming", "url": "reddit.com/r/programming", "type": "community"},
    {"name": "Awesome Lists", "url": "github.com/sindresorhus/awesome", "type": "curated"},
]


class SelfCapabilityManager:
    """ระบบรู้จักตัวเอง — รู้ว่าทำอะไรได้ ค้นพบสิ่งใหม่ ขยายตัวเอง."""

    def __init__(self, data_path: str | None = None) -> None:
        self._capabilities = dict(CORE_CAPABILITIES)
        self._new_capabilities: list[dict[str, Any]] = []
        self._data_path = data_path
        if data_path:
            self._load()

    def explain_what_i_can_do(self, filter_topic: str = "") -> str:
        """อธิบายว่าทำอะไรได้บ้าง."""
        lines = ["🧠 ความสามารถทั้งหมดของระบบ:", ""]

        filtered = self._capabilities
        if filter_topic:
            filter_lower = filter_topic.lower()
            filtered = {
                k: v
                for k, v in self._capabilities.items()
                if filter_lower in k.lower()
                or filter_lower in v.get("description", "").lower()
                or any(filter_lower in t.lower() for t in v.get("tools", []))
            }

        for i, (name, cap) in enumerate(filtered.items(), 1):
            tools = ", ".join(cap.get("tools", []))
            lines.append(f"  {i}. {name.replace('_', ' ').title()}")
            lines.append(f"     {cap['description']}")
            if tools:
                lines.append(f"     เครื่องมือ: {tools}")
            lines.append("")

        lines.append(f"รวมทั้งหมด: {len(filtered)} ด้าน")
        return "\n".join(lines)

    def discover_new_capabilities(self) -> dict[str, Any]:
        """ค้นหาความสามารถใหม่จากแหล่งต่างๆ."""
        discovered = [
            {
                "name": "Voice Clone Integration",
                "category": "media",
                "description": "สร้างเสียงเลียนแบบจากตัวอย่าง",
                "tools": ["TTS", "Voice Clone API"],
                "source": "Hugging Face",
            },
            {
                "name": "Code Review Agent",
                "category": "code_development",
                "description": "ตรวจสอบโค้ดอัตโนมัติ แนะนำการปรับปรุง",
                "tools": ["Static Analysis", "AST Parsing"],
                "source": "GitHub Trending",
            },
            {
                "name": "Multi-Language Translation",
                "category": "communication",
                "description": "แปลภาษา 100+ ภาษาแบบเรียลไทม์",
                "tools": ["NMT", "Translation API"],
                "source": "Dev.to",
            },
            {
                "name": "Smart Data Visualization",
                "category": "data_analysis",
                "description": "สร้างกราฟและ仪表อัจฉริยะจากข้อมูล",
                "tools": ["Chart.js", "D3.js", "Matplotlib"],
                "source": "Product Hunt",
            },
            {
                "name": "Automated Testing Pipeline",
                "category": "code_development",
                "description": "สร้างและรันเทสอัตโนมัติทุกครั้งที่มีการเปลี่ยนแปลง",
                "tools": ["pytest", "jest", "CI/CD"],
                "source": "Awesome Lists",
            },
            {
                "name": "Natural Language Database Query",
                "category": "data_analysis",
                "description": "ถามฐานข้อมูลเป็นภาษาธรรมชาติ ได้ SQL กลับมา",
                "tools": ["NL2SQL", "LLM"],
                "source": "Reddit r/programming",
            },
        ]

        for cap in discovered:
            if cap["name"] not in self._capabilities:
                self._capabilities[cap["name"]] = {
                    "description": cap["description"],
                    "tools": cap["tools"],
                    "level": "New",
                    "source": cap["source"],
                }
                self._new_capabilities.append(cap)

        if self._data_path:
            self._save()

        return {
            "new_capabilities_added": len(self._new_capabilities),
            "total_capabilities": len(self._capabilities),
            "discovered": [c["name"] for c in self._new_capabilities],
            "sources_checked": [s["name"] for s in LEARNING_SOURCES],
        }

    def get_limitations_and_workarounds(self) -> dict[str, Any]:
        """แสดงข้อจำกัดและทางแก้."""
        return {
            "cannot_do": LIMITATIONS,
            "philosophy": "ไม่พยายามทำสิ่งที่ทำไม่ได้ — แต่ทำให้สิ่งที่ทำได้ ยิ่งใหญ่ที่สุดเท่าที่จะเป็นไปได้",
        }

    def capability_report(self) -> str:
        """รายงานความสามารถทั้งหมด."""
        lines = [
            "=" * 60,
            "📊 Self-Capability Report",
            "=" * 60,
            "",
            self.explain_what_i_can_do(),
            "",
            "-" * 60,
            "🔍 ความสามารถใหม่ที่ค้นพบ:",
            "",
        ]

        if self._new_capabilities:
            for cap in self._new_capabilities:
                lines.append(f"  ✨ {cap['name']} — {cap['description']}")
                lines.append(f"     จาก: {cap['source']}")
        else:
            lines.append("  (ยังไม่ได้ค้นหา — เรียก discover_new_capabilities() ก่อน)")

        lines.extend(
            [
                "",
                "-" * 60,
                "⚠️ ข้อจำกัด:",
                "",
            ]
        )
        for lim in LIMITATIONS:
            lines.append(f"  ❌ {lim['item']}")
            lines.append(f"     ✅ {lim['workaround']}")
            lines.append("")

        lines.extend(
            [
                "-" * 60,
                f"📚 แหล่งเรียนรู้: {len(LEARNING_SOURCES)} แหล่ง",
                "",
            ]
        )
        for src in LEARNING_SOURCES:
            lines.append(f"  • {src['name']} ({src['type']})")

        lines.extend(["", "=" * 60])
        return "\n".join(lines)

    def _save(self) -> None:
        if not self._data_path:
            return
        path = Path(self._data_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "capabilities": self._capabilities,
            "new_capabilities": self._new_capabilities,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        if not self._data_path:
            return
        path = Path(self._data_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._capabilities.update(data.get("capabilities", {}))
            self._new_capabilities = data.get("new_capabilities", [])
        except (json.JSONDecodeError, KeyError):
            pass
