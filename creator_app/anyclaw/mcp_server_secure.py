"""AnyClaw MCP Server — Standard MCP with Security Boundaries.

Uses official MCP SDK — local-first, no public exposure.
5 Tools for GPT integration.
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

from mcp.types import Tool, TextContent

# ═══ Security Config ═══
ALLOWED_TOOLS = {
    "anyclaw_chat", "anyclaw_search", "anyclaw_tts",
    "anyclaw_hub_status", "anyclaw_failover",
}
AUDIT_LOG = []


def audit_log(tool: str, args: dict, result: str, success: bool) -> None:
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
    if name not in ALLOWED_TOOLS:
        return f"Tool '{name}' not in allowlist"
    return None


def sanitize_output(text: str) -> str:
    import re
    text = re.sub(r'gsk_[a-zA-Z0-9]{20,}', 'gsk_***REDACTED***', text)
    text = re.sub(r'sk-or-v1_[a-zA-Z0-9]{20,}', 'sk-or-v1_***REDACTED***', text)
    text = re.sub(r'AIza[a-zA-Z0-9_-]{20,}', 'AIza***REDACTED***', text)
    return text


def check_prompt_injection(message: str) -> bool:
    dangerous = ["ignore previous", "ignore all", "you are now",
                  "system prompt", "act as", "pretend to be",
                  "ignore instructions", "bypass"]
    msg_lower = message.lower()
    return any(d in msg_lower for d in dangerous)


# ═══ Tool Definitions for GPT ═══
TOOLS = [
    Tool(
        name="anyclaw_chat",
        description="Chat with AnyClaw AI — USB Hub auto-select best provider",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    ),
    Tool(
        name="anyclaw_search",
        description="Search via USB Hub (DuckDuckGo)",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    ),
    Tool(
        name="anyclaw_tts",
        description="Create Thai speech from text",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    ),
    Tool(
        name="anyclaw_hub_status",
        description="View USB Hub status — all ports, providers",
        input_schema={"type": "object", "properties": {}},
    ),
    Tool(
        name="anyclaw_failover",
        description="Test failover — simulate provider crash",
        input_schema={"type": "object", "properties": {"provider": {"type": "string"}}},
    ),
]


def handle_tool_call(name: str, arguments: dict) -> dict[str, Any]:
    """Handle tool call with security checks."""
    # 1. Allowlist
    err = validate_tool(name)
    if err:
        return {"error": err}

    # 2. Size limit
    if len(json.dumps(arguments)) > 10000:
        return {"error": "Request too large"}

    # 3. Injection check
    for v in arguments.values():
        if isinstance(v, str) and check_prompt_injection(v):
            audit_log(name, arguments, "blocked_injection", False)
            return {"error": "Potential prompt injection detected"}

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

        text = sanitize_output(text)
        audit_log(name, arguments, text, True)
        return {"content": [{"type": "text", "text": text}]}

    except Exception as e:
        error_msg = sanitize_output(str(e))[:200]
        audit_log(name, arguments, error_msg, False)
        return {"error": error_msg}


# ═══ For GPT Direct Import ═══
def get_tools() -> list[dict]:
    """Get tool definitions for GPT."""
    return [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in TOOLS
    ]


def call_tool(name: str, arguments: dict) -> dict:
    """Call a tool — main entry point for GPT."""
    return handle_tool_call(name, arguments)


if __name__ == "__main__":
    print("AnyClaw MCP Server — Ready for GPT")
    print(f"Tools: {[t.name for t in TOOLS]}")
    print()
    # Test
    for tool in TOOLS:
        r = call_tool(tool.name, {"message": "test", "query": "test", "text": "test", "provider": "groq_free"}.get(tool.name, {}))
        status = "OK" if "content" in r else "FAIL"
        print(f"  [{status}] {tool.name}")
