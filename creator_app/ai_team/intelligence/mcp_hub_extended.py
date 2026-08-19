"""MCP Hub Extended — เชื่อมทุกแอพผ่านมาตรฐานสากล.

MCP (Model Context Protocol) คือ "USB Hub สำหรับ AI":
- สร้าง MCP Server หนึ่งครั้ง → ทุก Agent ใช้ได้
- ไม่ต้องเขียนโค้ดเชื่อมต่อแบบ Custom สำหรับแต่ละแอพ
- รองรับ: Claude Code, Codex, Cursor, OpenClaw, AnyClaw

รวม MCP Servers ที่มีอยู่:
- google-automation-mcp (Gmail, Drive, Sheets, Calendar)
- mcp-headless-gmail (Gmail headless)
- fce-mcp-server (OTP extraction)
- AnyCrawl MCP (Web Scraping)
- ZeroDrop MCP (Temp Email)
- Betatel MCP (SMS Verification)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MCPServerStatus(str, Enum):
    """สถานะของ MCP Server."""
    DISCOVERED = "discovered"
    CONNECTED = "connected"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class MCPServerInfo:
    """ข้อมูล MCP Server หนึ่งตัว."""
    name: str
    description: str
    endpoint: str  # URL หรือ command
    tools: list[str] = field(default_factory=list)
    status: MCPServerStatus = MCPServerStatus.DISCOVERED
    capabilities: list[str] = field(default_factory=list)
    requires_auth: bool = False
    auth_type: str = ""  # oauth, api_key, none
    free_tier: str = ""
    category: str = ""  # email, scraping, storage, etc.
    last_health_check: float | None = None
    error_message: str = ""


@dataclass
class MCPTool:
    """เครื่องมือที่ MCP Server 提供."""
    name: str
    server: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    category: str = ""


class MCPHubExtended:
    """MCP Hub ที่ขยายความสามารถ — เชื่อมทุกอย่าง.

    วิธีใช้:
        hub = MCPHubExtended()

        #  discovers servers อัตโนมัติ
        hub.discover_all()

        # ดู servers ที่พบ
        servers = hub.list_servers()

        # เรียก tool ผ่าน MCP
        result = hub.call_tool("google-automation-mcp", "read_email", {
            "query": "verification code",
        })

        # ดูสถิติ
        stats = hub.get_stats()
    """

    # MCP Servers ที่รู้จัก
    KNOWN_SERVERS: list[MCPServerInfo] = [
        MCPServerInfo(
            name="google-automation-mcp",
            description="Headless Google Workspace — Gmail, Drive, Sheets, Calendar",
            endpoint="npx google-automation-mcp",
            tools=["read_email", "send_email", "list_drive", "read_sheet", "create_event"],
            capabilities=["gmail", "drive", "sheets", "calendar"],
            requires_auth=True,
            auth_type="oauth",
            free_tier="ฟรี — ไม่ต้อง GCP console",
            category="productivity",
        ),
        MCPServerInfo(
            name="mcp-headless-gmail",
            description="Gmail headless — ไม่เก็บ credentials ในเครื่อง",
            endpoint="npx mcp-headless-gmail",
            tools=["read_inbox", "send_email", "wait_for_otp", "search邮件"],
            capabilities=["gmail_headless", "otp_extraction"],
            requires_auth=True,
            auth_type="oauth",
            free_tier="ฟรี",
            category="email",
        ),
        MCPServerInfo(
            name="fce-mcp-server",
            description="MCP Server สำหรับ AI Agents — รอรับอีเมล + ดึง OTP",
            endpoint="npx fce-mcp-server",
            tools=["create_temp_email", "wait_for_otp", "read_inbox"],
            capabilities=["temp_email", "otp_extraction"],
            requires_auth=False,
            free_tier="ฟรี",
            category="email",
        ),
        MCPServerInfo(
            name="anycrawl-mcp",
            description="Web Scraping, Crawl, SERP — รองรับ Playwright, Cheerio",
            endpoint="npx anycrawl-mcp",
            tools=["scrape", "crawl", "serp", "screenshot"],
            capabilities=["web_scraping", "search", "screenshot"],
            requires_auth=True,
            auth_type="api_key",
            free_tier="1,500 credits ฟรี",
            category="scraping",
        ),
        MCPServerInfo(
            name="zerodrop-mcp",
            description="Disposable email สำหรับ AI Agents",
            endpoint="npx zerodrop-mcp",
            tools=["create_email", "read_inbox", "extract_otp"],
            capabilities=["temp_email", "otp_extraction"],
            requires_auth=False,
            free_tier="ฟรี",
            category="email",
        ),
        MCPServerInfo(
            name="betatel-mcp",
            description="MCP Server สำหรับ SMS Verification",
            endpoint="npx betatel-mcp",
            tools=["get_number", "wait_for_sms", "read_code"],
            capabilities=["sms_verification", "temp_number"],
            requires_auth=False,
            free_tier="ฟรี",
            category="sms",
        ),
        MCPServerInfo(
            name="notion-mcp",
            description="Notion integration — pages, databases, search",
            endpoint="npx @anthropic/notion-mcp",
            tools=["create_page", "search", "read_database", "update_page"],
            capabilities=["notion_pages", "notion_database", "search"],
            requires_auth=True,
            auth_type="api_key",
            free_tier="ฟรี สำหรับ personal",
            category="productivity",
        ),
        MCPServerInfo(
            name="slack-mcp",
            description="Slack integration — messages, channels, files",
            endpoint="npx @anthropic/slack-mcp",
            tools=["send_message", "read_channel", "upload_file"],
            capabilities=["slack_messages", "slack_channels"],
            requires_auth=True,
            auth_type="oauth",
            free_tier="ฟรี สำหรับ workspace",
            category="communication",
        ),
        MCPServerInfo(
            name="github-mcp",
            description="GitHub integration — repos, PRs, issues, actions",
            endpoint="npx @anthropic/github-mcp",
            tools=["create_issue", "list_prs", "push_code", "run_action"],
            capabilities=["github_repos", "github_pr", "github_actions"],
            requires_auth=True,
            auth_type="token",
            free_tier="ฟรี",
            category="development",
        ),
        MCPServerInfo(
            name="telegram-mcp",
            description="Telegram Bot integration",
            endpoint="npx telegram-mcp",
            tools=["send_message", "send_photo", "receive_update"],
            capabilities=["telegram_bot", "notifications"],
            requires_auth=True,
            auth_type="token",
            free_tier="ฟรี",
            category="communication",
        ),
    ]

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerInfo] = {}
        self._tools: dict[str, MCPTool] = {}
        self._call_history: list[dict[str, Any]] = []

    def discover_all(self) -> list[MCPServerInfo]:
        """ค้นหา MCP Servers ทั้งหมดที่รู้จัก."""
        for server in self.KNOWN_SERVERS:
            self._servers[server.name] = server
            #  register tools
            for tool_name in server.tools:
                tool = MCPTool(
                    name=tool_name,
                    server=server.name,
                    description=f"{tool_name} via {server.name}",
                    category=server.category,
                )
                self._tools[f"{server.name}:{tool_name}"] = tool
        return list(self._servers.values())

    def connect(self, server_name: str) -> bool:
        """เชื่อมต่อกับ MCP Server."""
        server = self._servers.get(server_name)
        if not server:
            return False
        server.status = MCPServerStatus.CONNECTED
        server.last_health_check = time.time()
        return True

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """เรียก tool ผ่าน MCP Server."""
        server = self._servers.get(server_name)
        if not server:
            return {"success": False, "error": f"Server '{server_name}' not found"}

        tool_key = f"{server_name}:{tool_name}"
        if tool_key not in self._tools:
            return {"success": False, "error": f"Tool '{tool_name}' not found on {server_name}"}

        # บันทึกประวัติ
        self._call_history.append({
            "server": server_name,
            "tool": tool_name,
            "args": arguments or {},
            "timestamp": time.time(),
        })

        # ในระบบจริงจะเชื่อม MCP protocol จริง
        # ตอนนี้ return mock result
        return {
            "success": True,
            "server": server_name,
            "tool": tool_name,
            "result": f"Tool '{tool_name}' executed on {server_name}",
            "timestamp": time.time(),
        }

    def list_servers(
        self,
        category: str | None = None,
        connected_only: bool = False,
    ) -> list[MCPServerInfo]:
        """ดึงรายการ servers."""
        servers = list(self._servers.values())
        if category:
            servers = [s for s in servers if s.category == category]
        if connected_only:
            servers = [s for s in servers if s.status in (MCPServerStatus.CONNECTED, MCPServerStatus.READY)]
        return servers

    def list_tools(
        self,
        server_name: str | None = None,
        category: str | None = None,
    ) -> list[MCPTool]:
        """ดึงรายการ tools."""
        tools = list(self._tools.values())
        if server_name:
            tools = [t for t in tools if t.server == server_name]
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def get_stats(self) -> dict[str, Any]:
        """ดูสถิติทั้งหมด."""
        servers = list(self._servers.values())
        return {
            "total_servers": len(servers),
            "connected": sum(1 for s in servers if s.status == MCPServerStatus.CONNECTED),
            "total_tools": len(self._tools),
            "total_calls": len(self._call_history),
            "categories": list(set(s.category for s in servers if s.category)),
        }

    def summary(self) -> str:
        """สรุปแบบ text."""
        stats = self.get_stats()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🔌 MCP Hub Extended — สถานะ                     ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"📊 Servers: {stats['total_servers']} (connected: {stats['connected']})",
            f"🔧 Tools: {stats['total_tools']}",
            f"📞 Calls: {stats['total_calls']}",
            f"📂 Categories: {', '.join(stats['categories'])}",
            "",
        ]

        for cat in sorted(set(s.category for s in self._servers.values() if s.category)):
            servers = [s for s in self._servers.values() if s.category == cat]
            lines.append(f"📂 {cat.upper()}")
            lines.append("─" * 50)
            for s in servers:
                status_emoji = "✅" if s.status == MCPServerStatus.CONNECTED else "⚪"
                auth_tag = f"[{s.auth_type}]" if s.requires_auth else "[free]"
                lines.append(f"  {status_emoji} {s.name} {auth_tag}")
                lines.append(f"     {s.free_tier}")
                lines.append(f"     Tools: {', '.join(s.tools[:3])}{'...' if len(s.tools) > 3 else ''}")
            lines.append("")

        return "\n".join(lines)
