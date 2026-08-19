"""AnyClaw MCP Server — ทำให้ AnyClaw เป็น MCP Tool ที่ Agent อื่นเรียกได้.

Claude Code, Codex, Cursor สามารถเรียก AnyClaw เป็น Tool ได้
ผ่าน HTTP endpoint บน port 8766

วิธีใช้:
    python -m creator_app.anyclaw.mcp_server
    # → http://localhost:8766

Endpoints:
    POST /chat          — ส่งข้อความ → ได้คำตอบ
    GET  /tools         — ดู tools ทั้งหมด
    POST /tools/call    — เรียก tool
    GET  /agents        — ดู agents ทั้งหมด
    GET  /status        — สถานะระบบ
    GET  /openapi.json  — OpenAPI schema
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from creator_app.anyclaw.bridge.agent_registry import AgentRegistry
from creator_app.anyclaw.core import AnyClawCore
from creator_app.anyclaw.hub.mcp_hub import AgentTool, MCPHub

# Global instances
_claw: AnyClawCore | None = None
_registry: AgentRegistry | None = None
_hub: MCPHub | None = None


def get_claw() -> AnyClawCore:
    global _claw
    if _claw is None:
        _claw = AnyClawCore(mode="super")
    return _claw


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _registry.scan()
    return _registry


def get_hub() -> MCPHub:
    global _hub
    if _hub is None:
        _hub = MCPHub()
        _setup_hub()
    return _hub


def _setup_hub() -> None:
    """ตั้งค่า hub ด้วย agents ที่พบ."""
    hub = _hub
    reg = get_registry()
    for agent in reg.get_available():
        tools = [
            AgentTool(f"{agent.name}_chat", f"Chat with {agent.display_name}"),
            AgentTool(f"{agent.name}_run", f"Run command via {agent.display_name}"),
        ]
        hub.register(agent.name, agent.display_name, tools=tools)


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP handler สำหรับ MCP Server."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/status":
            self._json_response(self._get_status())
        elif path == "/tools":
            self._json_response(self._get_tools())
        elif path == "/agents":
            self._json_response(self._get_agents())
        elif path == "/openapi.json":
            self._json_response(self._get_openapi())
        else:
            self._json_response({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/chat":
            self._handle_chat(body)
        elif path == "/tools/call":
            self._handle_tool_call(body)
        else:
            self._json_response({"error": "Not found"}, 404)

    def _handle_chat(self, body: dict) -> None:
        message = body.get("message", "")
        mode = body.get("mode", "super")
        if not message:
            self._json_response({"error": "message required"}, 400)
            return
        claw = get_claw()
        claw.mode = mode
        start = time.time()
        resp = claw.chat(message)
        self._json_response({
            "content": resp.content,
            "provider": resp.provider,
            "model": resp.model,
            "latency_ms": round((time.time() - start) * 1000, 1),
            "from_cache": resp.from_cache,
        })

    def _handle_tool_call(self, body: dict) -> None:
        agent = body.get("agent", "")
        tool = body.get("tool", "")
        params = body.get("params", {})
        hub = get_hub()
        result = hub.call_tool(agent, tool, params)
        self._json_response(result)

    def _get_status(self) -> dict:
        claw = get_claw()
        reg = get_registry()
        hub = get_hub()
        return {
            "service": "AnyClaw MCP Server",
            "version": "1.0.0",
            "anyclaw": claw.status(),
            "agents": reg.status(),
            "hub": hub.status(),
        }

    def _get_tools(self) -> list[dict]:
        hub = get_hub()
        return hub.get_tools()

    def _get_agents(self) -> list[dict]:
        hub = get_hub()
        return hub.list_agents()

    def _get_openapi(self) -> dict:
        return {
            "openapi": "3.0.0",
            "info": {"title": "AnyClaw MCP Server", "version": "1.0.0"},
            "paths": {
                "/chat": {
                    "post": {
                        "summary": "Send message → get response",
                        "requestBody": {
                            "content": {"application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"},
                                        "mode": {"type": "string", "enum": ["super", "free", "claude"]},
                                    },
                                },
                            }},
                        },
                    },
                },
                "/tools": {"get": {"summary": "List all tools"}},
                "/agents": {"get": {"summary": "List all agents"}},
                "/status": {"get": {"summary": "System status"}},
            },
        }

    def _json_response(self, data: dict | list, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, TypeError):
            return {}

    def log_message(self, format: str, *args: object) -> None:
        pass  # Silence logs


def run_server(host: str = "0.0.0.0", port: int = 8766) -> None:
    """รัน MCP Server."""
    server = HTTPServer((host, port), MCPHandler)
    print(f"🚀 AnyClaw MCP Server running on http://{host}:{port}")
    print("   POST /chat        — ส่งข้อความ")
    print("   GET  /tools       — ดู tools ทั้งหมด")
    print("   GET  /agents      — ดู agents ทั้งหมด")
    print("   GET  /status      — สถานะระบบ")
    print("   GET  /openapi.json — OpenAPI schema")
    print("\n   Ctrl+C เพื่อหยุด")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.server_close()


if __name__ == "__main__":
    run_server()
