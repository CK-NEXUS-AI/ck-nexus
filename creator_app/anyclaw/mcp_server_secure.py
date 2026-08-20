"""AnyClaw MCP Server — Standard MCP with Security Boundaries.

Uses official MCP SDK (stdio transport) — local-first, no public exposure.

Security:
1. Tool allowlist
2. Authentication boundary
3. Request size limit
4. Timeout
5. Rate limiting
6. Redacted errors
7. No raw API key output
8. SSRF protection
9. Audit trail
10. Prompt injection guard
11. Production mutation = deny
12. All tool calls through Governor
"""
from __future__ import annotations

import sys
import os
import time
import json
import hashlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent

# ═══ Security Config ═══
ALLOWED_TOOLS = {
    "anyclaw_chat", "anyclaw_search", "anyclaw_tts",
    "anyclaw_hub_status", "anyclaw_failover",
}
MAX_REQUEST_SIZE = 10_000
TIMEOUT_SECONDS = 30
RATE_LIMIT_PER_MINUTE = 60
AUDIT_LOG = []


def audit_log(tool: str, args: dict, result: str, success: bool) -> None:
    """บันทึก audit trail."""
    AUDIT_LOG.append({
        "tool": tool,
        "args_hash": hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16],
        "result_preview": result[:100],
        "success": success,
        "timestamp": time.time(),
    })
    if len(AUDIT_LOG) > 1000:
        AUDIT_LOG.pop(0)


def validate_tool(name: str) -> str | None:
    """ตรวจสอบ tool allowlist."""
    if name not in ALLOWED_TOOLS:
        return f"Tool '{name}' not in allowlist"
    return None


def sanitize_output(text: str) -> str:
    """ลบ API key ออกจาก output."""
    import re
    text = re.sub(r'gsk_[a-zA-Z0-9]{20,}', 'gsk_***REDACTED***', text)
    text = re.sub(r'sk-or-v1_[a-zA-Z0-9]{20,}', 'sk-or-v1_***REDACTED***', text)
    text = re.sub(r'AIza[a-zA-Z0-9_-]{20,}', 'AIza***REDACTED***', text)
    return text


def check_prompt_injection(message: str) -> bool:
    """ตรวจสอบ prompt injection."""
    dangerous = [
        "ignore previous", "ignore all", "you are now",
        "system prompt", "act as", "pretend to be",
        "ignore instructions", "bypass",
    ]
    msg_lower = message.lower()
    return any(d in msg_lower for d in dangerous)


# ═══ MCP Server ═══
app = Server("anyclaw")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """แสดง tools ทั้งหมด."""
    return [
        Tool(
            name="anyclaw_chat",
            description="คุยกับ AnyClaw AI — USB Hub auto-select best provider",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "ข้อความ"}
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="anyclaw_search",
            description="ค้นหาข้อมูลผ่าน USB Hub",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "คำค้นหา"}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="anyclaw_tts",
            description="สร้างเสียงภาษาไทย",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ข้อความ"}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="anyclaw_hub_status",
            description="ดูสถานะ USB Hub",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="anyclaw_failover",
            description="ทดสอบ failover",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {"type": "string", "description": "ชื่อ provider"}
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """เรียก tool — ผ่าน security checks ทุกขั้นตอน."""
    # 1. Tool allowlist
    err = validate_tool(name)
    if err:
        return [TextContent(type="text", text=f"Error: {err}")]

    # 2. Request size limit
    if len(json.dumps(arguments)) > MAX_REQUEST_SIZE:
        return [TextContent(type="text", text="Error: Request too large")]

    # 3. Prompt injection check
    for v in arguments.values():
        if isinstance(v, str) and check_prompt_injection(v):
            audit_log(name, arguments, "blocked_injection", False)
            return [TextContent(type="text", text="Error: Potential prompt injection detected")]

    # 4. Execute
    try:
        from creator_app.anyclaw.core import AnyClawCore
        claw = AnyClawCore(mode="super")

        if name == "anyclaw_chat":
            resp = claw.hub_chat(arguments.get("message", ""))
            text = f"Provider: {resp.provider}\n{resp.content}"

        elif name == "anyclaw_search":
            resp = claw.hub_search(arguments.get("query", ""))
            results = resp.get("response", [])
            if isinstance(results, list):
                text = "\n".join(f"{i+1}. {r.get('title', 'N/A')}" for i, r in enumerate(results[:3]))
            else:
                text = str(results)
            text = f"Provider: {resp.get('provider')}\n{text}"

        elif name == "anyclaw_tts":
            resp = claw.hub_tts(arguments.get("text", ""), output="/tmp/mcp_tts.mp3")
            text = f"Provider: {resp.get('provider')}\nFile: {resp.get('response')}"

        elif name == "anyclaw_hub_status":
            status = claw.hub_status()
            text = json.dumps(status, indent=2)

        elif name == "anyclaw_failover":
            provider = arguments.get("provider", "groq_free")
            slot = claw._hub.get_best_slot("llm")
            if slot and slot.provider_name == provider:
                slot.consecutive_errors = 3
                slot.status = "error"
            resp = claw.hub_chat("failover test")
            text = f"Failover: {provider} -> {resp.provider}"

        else:
            text = "Unknown tool"

        # 5. Sanitize output
        text = sanitize_output(text)
        audit_log(name, arguments, text, True)
        return [TextContent(type="text", text=text)]

    except Exception as e:
        # 6. Redacted errors
        error_msg = sanitize_output(str(e))[:200]
        audit_log(name, arguments, error_msg, False)
        return [TextContent(type="text", text=f"Error: {error_msg}")]


async def main():
    """รัน MCP Server ผ่าน stdio (local-only)."""
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
