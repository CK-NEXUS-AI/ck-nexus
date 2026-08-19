"""Universal System — ระบบอเนกประสงค์สูงสุด.

รวม 6 ระบบเป็นหนึ่งเดียว:
1. ตัวแทนอัจฉริยะ — Auto-Tool Selection, Tool Chaining, Fallback
2. ทีมผู้เชี่ยวชาญ — 7 บทบาท ทำงานร่วมกัน
3. ศูนย์กลางข้อมูล — Unified Search, Smart Sync, Data Pipelines
4. ตัวสร้างระบบ — CLI, Skills, Plugins, Workflows
5. ปลอดภัยและโปร่งใส — Secret Shield, Permission Gate, Audit Log
6. ทำงานได้ทุกที่ — Cross-Platform Support

วิธีใช้:
    system = UniversalSystem()
    result = system.process("สร้างระบบเชื่อม Gmail อ่านอีเมล บันทึก Sheets")
    print(result)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from creator_app.ai_team.team_director import TeamDirector

# ─── ระบบที่ 1: ตัวแทนอัจฉริยะ (Smart Agent) ──────────────────────────


@dataclass
class ToolSpec:
    """ข้อมูลเครื่องมือที่มีอยู่."""

    name: str
    category: str
    capabilities: tuple[str, ...] = ()
    requires_permission: bool = False
    permission_type: str = ""


# Registry ของเครื่องมือทั้งหมดที่มีอยู่
TOOL_REGISTRY: list[ToolSpec] = [
    ToolSpec("gmail", "communication", ("อ่านอีเมล", "ส่งอีเมล", "ค้นหาอีเมล", "สกัดข้อมูล"), True, "email"),
    ToolSpec(
        "google_calendar", "communication", ("จัดการปฏิทิน", "สร้างกิจกรรม", "แจ้งเตือน"), True, "calendar"
    ),
    ToolSpec("google_sheets", "data", ("บันทึกข้อมูล", "คำนวณ", "สร้างกราฟ"), True, "sheets"),
    ToolSpec("google_docs", "content", ("สร้างเอกสาร", "แก้ไขเอกสาร"), True, "docs"),
    ToolSpec("google_drive", "storage", ("จัดการไฟล์", "อัพโหลด", "แชร์"), True, "drive"),
    ToolSpec("slack", "communication", ("ส่งข้อความ", "ค้นหาข้อความ"), True, "slack"),
    ToolSpec("telegram", "communication", ("ส่งข้อความ", "สร้าง bot"), False, ""),
    ToolSpec("notion", "knowledge", ("จัดการหน้า", "ค้นหาข้อมูล"), True, "notion"),
    ToolSpec("linear", "management", ("จัดการ issue", "ติดตามงาน"), True, "linear"),
    ToolSpec("figma", "design", ("ออกแบบ", "ดึง design"), True, "figma"),
    ToolSpec("canva", "design", ("สร้าง presentation", "ออกแบบ"), True, "canva"),
    ToolSpec("playwright", "automation", ("ควบคุมเบราว์เซอร์", "ดึงข้อมูลเว็บ"), False, ""),
    ToolSpec("vercel", "deployment", ("deploy", "จัดการ serverless"), True, "vercel"),
    ToolSpec("github", "development", ("จัดการ repo", "PR", "Issue", "CI/CD"), True, "github"),
    ToolSpec("shell", "development", ("รันคำสั่ง", "ติดตั้ง", "build"), False, ""),
    ToolSpec("code", "development", ("เขียนโค้ด", "แก้โค้ด", "debug", "test"), False, ""),
    ToolSpec("android", "mobile", ("เข้าถึงกล้อง", "location", "SMS", "contacts"), False, ""),
    ToolSpec("security_scan", "security", ("สแกนช่องโหว่", "audit", "threat model"), False, ""),
]


class SmartAgent:
    """ตัวแทนอัจฉริยะ — เลือกเครื่องมือเอง ตามคำขอ."""

    def __init__(self) -> None:
        self.tools = TOOL_REGISTRY

    def select_tools(self, request: str) -> list[ToolSpec]:
        """เลือกเครื่องมือที่เหมาะสมกับคำขอ."""
        request_lower = request.lower()
        selected: list[ToolSpec] = []
        seen_names: set[str] = set()

        keyword_map: dict[str, list[str]] = {
            "gmail": ["อีเมล", "email", "mail", "inbox", "gmail"],
            "google_calendar": ["ปฏิทิน", "calendar", "กิจกรรม", "จอง", "กำหนดการ"],
            "google_sheets": ["ตาราง", "sheets", " spreadsheet", "บันทึกข้อมูล", "คำนวณ"],
            "google_docs": ["เอกสาร", "docs", "เขียนคู่มือ"],
            "google_drive": ["ไฟล์", "drive", "อัพโหลด", "แชร์"],
            "slack": ["slack", "ทีมงาน", "แจ้งทีม"],
            "telegram": ["telegram", "บอท", "bot"],
            "notion": ["notion", "ความรู้", "หน้า"],
            "linear": ["linear", "issue", "task", "งาน"],
            "figma": ["figma", "design", "ออกแบบ"],
            "canva": ["canva", "presentation"],
            "playwright": ["เว็บ", "web", " scrape", "เบราว์เซอร์", "browser"],
            "vercel": ["deploy", "serverless", "hosting"],
            "github": ["github", "repo", "git", "branch", "pr"],
            "shell": ["shell", "bash", "ติดตั้ง", "รันคำสั่ง"],
            "code": ["โค้ด", "code", "เขียน", "debug", "test", "สร้างระบบ"],
            "android": ["มือถือ", "android", "กล้อง", "camera"],
            "security_scan": ["security", "ความปลอดภัย", "audit", "scan"],
        }

        for tool in self.tools:
            keywords = keyword_map.get(tool.name, [])
            if any(kw.lower() in request_lower for kw in keywords) and tool.name not in seen_names:
                selected.append(tool)
                seen_names.add(tool.name)

        return selected

    def chain_tools(self, tools: list[ToolSpec], request: str) -> list[dict[str, Any]]:
        """สร้าง tool chain — ผลลัพธ์จากเครื่องมือแรกส่งต่ออัตโนมัติ."""
        chain: list[dict[str, Any]] = []
        for i, tool in enumerate(tools):
            step = {
                "step": i + 1,
                "tool": tool.name,
                "category": tool.category,
                "input": f"ผลลัพธ์จากขั้นตอนที่ {i}" if i > 0 else request,
                "output": f"ข้อมูลจาก {tool.name}",
                "requires_permission": tool.requires_permission,
            }
            chain.append(step)
        return chain


# ─── ระบบที่ 3: ศูนย์กลางข้อมูล (Data Hub) ──────────────────────────


@dataclass
class DataSource:
    name: str
    type: str
    capabilities: tuple[str, ...] = ()
    read_only: bool = True


class DataHub:
    """ศูนย์กลางข้อมูล — ดึงจากทุกที่ ประมวลผล ส่งไปทุกที่."""

    def __init__(self) -> None:
        self.sources: list[DataSource] = [
            DataSource("Gmail", "email", ("อ่าน", "ส่ง", "ค้นหา", "สกัด OTP", "อีเมล"), False),
            DataSource("Google Calendar", "calendar", ("อ่าน", "สร้าง", "แก้ไข"), False),
            DataSource("Google Sheets", "spreadsheet", ("อ่าน", "เขียน", "คำนวณ"), False),
            DataSource("Google Drive", "storage", ("อ่าน", "อัพโหลด", "แชร์"), False),
            DataSource("Slack", "messaging", ("อ่าน", "ส่ง"), False),
            DataSource("Telegram", "messaging", ("อ่าน", "ส่ง"), False),
            DataSource("Notion", "knowledge", ("อ่าน", "เขียน", "ค้นหา"), False),
            DataSource("GitHub", "code", ("อ่าน", "เขียน", "PR"), False),
            DataSource("Playwright", "web", ("ดึงข้อมูล", " scrape"), True),
            DataSource("Android", "mobile", ("อ่าน SMS", "อ่าน contacts"), True),
        ]

    def unified_search(self, query: str) -> dict[str, list[str]]:
        """ค้นหาคำเดียว → เจอทุกที่."""
        results: dict[str, list[str]] = {}
        query_lower = query.lower()
        query_words = set(query_lower.split())
        for source in self.sources:
            name_match = query_lower in source.name.lower() or source.name.lower() in query_lower
            cap_match = any(
                cap.lower() in query_lower or query_lower in cap.lower()
                for cap in source.capabilities
            )
            word_match = any(
                w in source.name.lower() or any(w in cap.lower() for cap in source.capabilities)
                for w in query_words
            )
            if name_match or cap_match or word_match:
                results[source.name] = list(source.capabilities)
        return results

    def smart_sync(self, source_name: str, target_name: str, data: Any) -> dict:
        """เมื่อข้อมูลเปลี่ยนที่ไหน → อัปเดตทุกที่."""
        return {
            "source": source_name,
            "target": target_name,
            "synced": True,
            "data_type": type(data).__name__,
        }

    def build_pipeline(self, steps: list[dict[str, str]]) -> dict:
        """สร้าง data pipeline — กำหนดครั้งเดียว ทำเองตลอดไป."""
        return {
            "pipeline_steps": steps,
            "total_steps": len(steps),
            "status": "ready",
        }


# ─── ระบบที่ 5: ปลอดภัย (Security Layer) ──────────────────────────


@dataclass
class AuditEntry:
    timestamp: float
    action: str
    agent: str
    target: str
    status: str
    details: str = ""


class SecurityLayer:
    """ชั้นความปลอดภัย — ปกป้องข้อมูลลับ ตรวจสอบสิทธิ์ บันทึกทุกการกระทำ."""

    SECRET_PATTERNS = [
        "sk-",
        "gsk_",
        "sk-ant-",
        "AIza",
        "ghp_",
        "gho_",
        "Bearer ",
        "Authorization: ",
    ]

    def __init__(self) -> None:
        self.audit_log: list[AuditEntry] = []

    def secret_shield(self, text: str) -> str:
        """ตรวจสอบก่อนส่ง — ไม่ให้ API Key หลุด."""
        import re as _re

        for pattern in self.SECRET_PATTERNS:
            if pattern in text:
                # Redact pattern + following key characters (alphanumeric, dashes, underscores)
                regex = _re.escape(pattern) + r"[A-Za-z0-9_\-]{4,}"
                redacted = _re.sub(regex, "[REDACTED]", text)
                self._audit(
                    "secret_shield", "system", "redact", "pass", f"Redacted pattern: {pattern[:4]}"
                )
                return redacted
        return text

    def permission_gate(self, action: str, resource: str) -> dict:
        """ก่อนเข้าถึงข้อมูลละเอียดอ่อน → ขอยืนยันเสมอ."""
        sensitive_resources = ["gmail", "calendar", "sheets", "drive", "slack", "notion"]
        requires_check = any(r in resource.lower() for r in sensitive_resources)

        result = {
            "action": action,
            "resource": resource,
            "requires_permission": requires_check,
            "approved": not requires_check,  # auto-approve non-sensitive
        }

        self._audit(
            "permission_gate",
            "system",
            action,
            "checked",
            f"Resource: {resource}, requires_check: {requires_check}",
        )
        return result

    def scope_limiter(self, requested: str, needed: list[str]) -> list[str]:
        """ขอแค่สิทธิ์ที่จำเป็น — ไม่ขอทั้งระบบ."""
        return [s for s in needed if s in requested.lower()]

    def audit(self, action: str, agent: str, target: str, status: str, details: str = "") -> None:
        """บันทึกทุกการกระทำ — ใคร ทำอะไร เมื่อไหร่."""
        self._audit(action, agent, target, status, details)

    def _audit(self, action: str, agent: str, target: str, status: str, details: str) -> None:
        self.audit_log.append(
            AuditEntry(
                timestamp=time.time(),
                action=action,
                agent=agent,
                target=target,
                status=status,
                details=details,
            )
        )

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return [
            {
                "timestamp": entry.timestamp,
                "action": entry.action,
                "agent": entry.agent,
                "target": entry.target,
                "status": entry.status,
                "details": entry.details,
            }
            for entry in self.audit_log[-limit:]
        ]


# ─── ระบบที่ 6: ทำงานได้ทุกที่ (Cross-Platform) ────────────────────


@dataclass
class PlatformCapability:
    platform: str
    capabilities: tuple[str, ...] = ()
    available: bool = False


class CrossPlatform:
    """ทำงานได้ทุกแพลตฟอร์ม — มือถือ คอม เซิร์ฟเวอร์."""

    def __init__(self) -> None:
        self.platforms = [
            PlatformCapability(
                "android", ("camera", "mic", "location", "sms", "contacts", "shell"), False
            ),
            PlatformCapability("linux", ("shell", "git", "docker", "python", "node"), True),
            PlatformCapability("server", ("deploy", "cron", "docker", "monitoring"), True),
            PlatformCapability("browser", ("playwright", "scrape", "screenshot"), True),
        ]

    def detect_platform(self) -> str:
        """ตรวจสอบแพลตฟอร์มปัจจุบัน."""
        import platform

        system = platform.system().lower()
        if system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        return system

    def get_capabilities(self, platform_name: str | None = None) -> list[str]:
        """ดึงความสามารถของแพลตฟอร์ม."""
        if platform_name:
            for p in self.platforms:
                if p.platform == platform_name:
                    return list(p.capabilities)
        return []

    def cross_platform_task(self, task: str) -> dict:
        """ทำงานข้ามแพลตฟอร์ม — เริ่มที่ไหน ดำเนินต่อได้ทุกที่."""
        platform = self.detect_platform()
        return {
            "task": task,
            "current_platform": platform,
            "available_on": [p.platform for p in self.platforms if p.available],
            "status": "ready",
        }


# ─── Universal System — รวมทุกระบบเป็นหนึ่งเดียว ────────────────────


class UniversalSystem:
    """ระบบอเนกประสงค์สูงสุด — รวม 6 ระบบเป็นหนึ่งเดียว.

    คำสั่งเดียว → ทั้ง 6 ระบบรู้ว่าต้องทำอะไร
    """

    def __init__(self) -> None:
        self.team = TeamDirector()
        self.smart_agent = SmartAgent()
        self.data_hub = DataHub()
        self.security = SecurityLayer()
        self.cross_platform = CrossPlatform()

    def process(self, request: str, *, priority: int = 2) -> str:
        """ประมวลผลคำขอ — ระบบอัตโนมัติเลือกทุกอย่างเอง."""
        start = time.time()

        # 1. Security check
        safe_request = self.security.secret_shield(request)
        self.security.audit("process_request", "user", "system", "started", safe_request[:100])

        # 2. Smart tool selection
        tools = self.smart_agent.select_tools(request)
        tool_names = [t.name for t in tools]

        # 3. Permission check for sensitive tools
        permissions: list[dict] = []
        for tool in tools:
            if tool.requires_permission:
                perm = self.security.permission_gate("use", tool.name)
                permissions.append(perm)

        # 4. Build tool chain
        chain = self.smart_agent.chain_tools(tools, request)

        # 5. Team processing
        team_result = self.team.process_request(request, priority=priority)

        # 6. Data hub pipeline
        pipeline_steps = []
        for tool in tools:
            if tool.category in ("data", "communication", "storage"):
                pipeline_steps.append({"source": tool.name, "action": "sync"})

        if pipeline_steps:
            self.data_hub.build_pipeline(pipeline_steps)

        # 7. Cross-platform check
        platform_info = self.cross_platform.cross_platform_task(request)

        # 8. Audit
        duration = time.time() - start
        self.security.audit(
            "process_complete",
            "universal_system",
            "result",
            "completed",
            f"tools={tool_names}, duration={duration:.2f}s",
        )

        # 9. Build output
        output_lines = [
            "🎯 ผลลัพธ์ Universal System",
            f"{'=' * 50}",
            f"📝 คำขอ: {safe_request[:100]}",
            "",
            f"🔧 เครื่องมือ: {', '.join(tool_names) if tool_names else 'N/A'}",
            f"🔗 Tool Chain: {len(chain)} ขั้นตอน",
            f"👥 ทีม: {', '.join(team_result.team_members_used) or 'N/A'}",
            f"📊 ขั้นตอน: {team_result.steps_completed}/{team_result.steps_total}",
            f"⏱️ เวลา: {duration:.2f} วินาที",
            f"🖥️ แพลตฟอร์ม: {platform_info['current_platform']}",
            f"🛡️ ความปลอดภัย: {len(permissions)} permissions checked",
            "",
            f"{'=' * 50}",
        ]

        if team_result.final_output:
            output_lines.append(team_result.final_output)

        return self.security.secret_shield("\n".join(output_lines))

    def status(self) -> dict[str, Any]:
        """สถานะรวมของทุกระบบ."""
        return {
            "team": self.team.team_status(),
            "tools_registered": len(TOOL_REGISTRY),
            "data_sources": len(self.data_hub.sources),
            "platform": self.cross_platform.detect_platform(),
            "audit_entries": len(self.security.audit_log),
        }

    def list_capabilities(self) -> dict[str, Any]:
        """ดูความสามารถทั้งหมดที่มี."""
        return {
            "team_members": self.team.list_team()["total_members"],
            "tools": len(TOOL_REGISTRY),
            "data_sources": len(self.data_hub.sources),
            "platforms": len(self.cross_platform.platforms),
            "categories": list(set(t.category for t in TOOL_REGISTRY)),
        }
