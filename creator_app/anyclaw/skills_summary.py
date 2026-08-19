"""Skills Summary — สรุปสกิลทั้งหมดของ CK-NEXUS + Codex Running.

รวมทุกความสามารถ + เครื่องมือ + การเชื่อมต่อ
เป็น central reference สำหรับ system ทั้งหมด
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Skill:
    """สกิลหนึ่งอย่าง."""

    name: str
    category: str
    description: str
    source: str  # ck-nexus, codex, external
    available: bool = True


# ═══════════════════════════════════════════════════════
# รายการสกิลทั้งหมด
# ═══════════════════════════════════════════════════════

ALL_SKILLS: list[Skill] = [
    # ─── CK-NEXUS Core Skills ─────────────────────────
    Skill("Universal System", "core", "รวม 6 ระบบเป็นหนึ่ง — รับคำสั่งเดียว ทำทุกอย่าง", "ck-nexus"),
    Skill("Policy Engine", "core", "Evidence-First — ทุกการกระทำต้องมีหลักฐาน", "ck-nexus"),
    Skill("State Manager", "core", "จัดการสถานะ + ความจำ — ไม่หาย ไม่ซ้ำ", "ck-nexus"),
    Skill("SelfCapabilityManager", "core", "รู้ว่าตัวเองทำอะไรได้/ไม่ได้ — ค้นพบสกิลใหม่", "ck-nexus"),

    # ─── Credentials & Security ────────────────────────
    Skill("Blind Vault", "security", "เก็บ API Key แบบเข้ารหัส — agent ไม่เห็นค่าจริง", "ck-nexus"),
    Skill("Multi-Key Pool", "security", "key หลายตัว — auto-failover เมื่อพัง", "ck-nexus"),
    Skill("Key Health Monitor", "security", "ตรวจสุขภาพ key — แจ้งเตือนใกล้หมด", "ck-nexus"),
    Skill("Auto-Provisioner", "security", "สร้าง key ใหม่อัตโนมัติ", "ck-nexus"),
    Skill("Free Provider Registry", "security", "รวม 20+ providers ฟรี", "ck-nexus"),
    Skill("Secret Shield", "security", "ตรวจสอบก่อนส่ง — ไม่ให้ key หลุด", "ck-nexus"),
    Skill("Permission Gate", "security", "ขอสิทธิ์ก่อนเข้าถึงข้อมูลละเอียดอ่อน", "ck-nexus"),
    Skill("Audit Log", "security", "บันทึกทุกการกระทำ — ใครทำอะไรเมื่อไหร่", "ck-nexus"),

    # ─── Intelligence ──────────────────────────────────
    Skill("Smart Cache", "intelligence", "แคช 2 ชั้น — ตอบซ้ำทันที ไม่เรียก API ซ้ำ", "ck-nexus"),
    Skill("Auto Model Router", "intelligence", "เลือกโมเดลอัตโนมัติ — ง่าย=เร็ว, ยาก=ลึก", "ck-nexus"),
    Skill("Parallel Executor", "intelligence", "รันงานขนาน — เร็วขึ้น 3-5 เท่า", "ck-nexus"),
    Skill("Self-Correction Loop", "intelligence", "ตรวจสอบก่อนส่ง — ลดความผิดพลาด 80%", "ck-nexus"),
    Skill("Multi-Perspective", "intelligence", "คิด 4 มุม (Tech/Security/User/Business)", "ck-nexus"),
    Skill("Semantic Memory", "intelligence", "จำแบบเข้าใจ — ไม่ใช่แค่ท่องจำ", "ck-nexus"),

    # ─── AI Team ───────────────────────────────────────
    Skill("Director", "team", "วางแผน — แบ่งงาน — ตัดสินใจภาพรวม", "ck-nexus"),
    Skill("Engineer", "team", "เขียนโค้ด — รันคำสั่ง — แก้ปัญหาเทคนิค", "ck-nexus"),
    Skill("Guardian", "team", "ตรวจสอบความปลอดภัย — ป้องกันข้อมูลรั่ว", "ck-nexus"),
    Skill("Analyst", "team", "วิเคราะห์ข้อมูล — เปรียบเทียบ — สรุปผล", "ck-nexus"),
    Skill("Researcher", "team", "ค้นหาข้อมูล — เจาะลึก — ตรวจสอบแหล่งที่มา", "ck-nexus"),
    Skill("Designer", "team", "จัดรูปแบบ — UI/UX — นำเสนอผลลัพธ์", "ck-nexus"),
    Skill("Connector", "team", "เชื่อมต่อระบบ — เรียก API — ซิงค์ข้อมูล", "ck-nexus"),

    # ─── Provider Adapters ─────────────────────────────
    Skill("Groq Adapter", "provider", "เชื่อม Groq — เร็วสุด ~42ms, ฟรี", "ck-nexus"),
    Skill("OpenAI Adapter", "provider", "เชื่อม OpenAI — GPT-4o, GPT-4o-mini", "ck-nexus"),
    Skill("Google AI Adapter", "provider", "เชื่อม Gemini — ฟรี 15 req/min", "ck-nexus"),
    Skill("Ollama Adapter", "provider", "เชื่อม Local LLM — ฟรี 100%, ไม่จำกัด", "ck-nexus"),

    # ─── Channel Connectors ────────────────────────────
    Skill("Telegram Bot", "channel", "รับ/ส่งข้อความ Telegram", "ck-nexus"),
    Skill("Webhook", "channel", "รับ/ส่ง HTTP webhooks", "ck-nexus"),
    Skill("MCP Server", "channel", "เชื่อม ChatGPT/Claude ภายนอก", "ck-nexus"),

    # ─── Storage ───────────────────────────────────────
    Skill("SD Card Manager", "storage", "เก็บข้อมูลขนาดใหญ่ — ออฟไลน์ได้", "ck-nexus"),
    Skill("Google Drive", "storage", "เชื่อม Google Drive/Sheets/Docs", "ck-nexus"),

    # ─── AnyClaw ───────────────────────────────────────
    Skill("AnyClaw Core", "anyclaw", "Terminal Chat — Free → Claude fallback", "ck-nexus"),
    Skill("Agent Registry", "anyclaw", "ตรวจจับ agents ทั้งหมดในเครื่อง", "ck-nexus"),
    Skill("Local Model Bridge", "anyclaw", "เชื่อม Ollama/MLX เข้า Coding Agent", "ck-nexus"),
    Skill("MCP Hub", "anyclaw", "Central Hub — ทุก agent คุยกันได้", "ck-nexus"),

    # ─── Codex Native Skills ───────────────────────────
    Skill("Shell/Bash", "codex", "รันคำสั่ง terminal ใดก็ได้", "codex"),
    Skill("Git/GitHub", "codex", "จัดการ repo, branch, commit, PR, CI/CD", "codex"),
    Skill("File Operations", "codex", "อ่าน/เขียน/แก้ไข/ลบไฟล์", "codex"),
    Skill("Code Analysis", "codex", "วิเคราะห์โค้ด — debug, refactor, optimize", "codex"),
    Skill("Web Search", "codex", "ค้นหาข้อมูลบนอินเทอร์เน็ต", "codex"),
    Skill("Playwright", "codex", "ควบคุมเบราว์เซอร์ — scraping, automation", "codex"),
    Skill("Image Generation", "codex", "สร้าง/แก้ไขรูปภาพ", "codex"),
    Skill("Security Scan", "codex", "สแกนช่องโหว่ — Ruff, Bandit, Secret scan", "codex"),

    # ─── External Tools ────────────────────────────────
    Skill("Vercel Deploy", "external", "Deploy ขึ้น Vercel — ฟรี", "external"),
    Skill("Supabase", "external", "PostgreSQL + Auth + Realtime — ฟรี", "external"),
    Skill("Composio", "external", "เชื่อม 200+ Apps เข้าด้วยกัน", "external"),
]


class SkillsSummary:
    """สรุปสกิลทั้งหมด.

    วิธีใช้:
        summary = SkillsSummary()
        print(summary.full_report())

        # ค้นหา
        results = summary.search("security")
    """

    def __init__(self) -> None:
        self._skills = ALL_SKILLS

    def by_category(self, category: str) -> list[Skill]:
        return [s for s in self._skills if s.category == category]

    def by_source(self, source: str) -> list[Skill]:
        return [s for s in self._skills if s.source == source]

    def search(self, keyword: str) -> list[Skill]:
        kw = keyword.lower()
        return [
            s for s in self._skills
            if kw in s.name.lower()
            or kw in s.description.lower()
            or kw in s.category.lower()
        ]

    def categories(self) -> dict[str, int]:
        cats: dict[str, int] = {}
        for s in self._skills:
            cats[s.category] = cats.get(s.category, 0) + 1
        return cats

    def full_report(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║  🧠 CK-NEXUS + Codex — Skills Summary                  ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            f"📦 รวมทั้งหมด: {len(self._skills)} skills",
            "",
        ]

        cats = self.categories()
        for cat, count in sorted(cats.items()):
            lines.append(f"  {cat}: {count} skills")

        lines.append("")
        lines.append("─" * 55)

        for cat in sorted(cats.keys()):
            skills = self.by_category(cat)
            lines.append(f"\n🏷️ {cat.upper()} ({len(skills)})")
            for s in skills:
                icons = {"ck-nexus": "🔧", "codex": "🤖", "external": "🌐"}
                source_icon = icons.get(s.source, "❓")
                lines.append(f"  {source_icon} {s.name} — {s.description}")

        lines.append("")
        lines.append("─" * 55)
        lines.append(f"\n💡 CK-NEXUS: {len(self.by_source('ck-nexus'))} skills")
        lines.append(f"🤖 Codex Native: {len(self.by_source('codex'))} skills")
        lines.append(f"🌐 External: {len(self.by_source('external'))} skills")
        return "\n".join(lines)
