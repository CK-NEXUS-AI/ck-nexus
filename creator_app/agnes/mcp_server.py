"""MCP Server — เชื่อม AnyClaw ↔ ChatGPT.

รัน: python -m creator_app.agnes.mcp_server
พอร์ต: http://localhost:8765

ใน ChatGPT → Settings → Beta features → Custom GPTs → Actions
ใส่: http://localhost:8765/openapi.json
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from creator_app.ai_team.universal_system import UniversalSystem
from creator_app.core.self_capability_manager import SelfCapabilityManager

# สร้าง instances
_system: UniversalSystem | None = None
_capability_manager: SelfCapabilityManager | None = None


def get_system() -> UniversalSystem:
    global _system
    if _system is None:
        _system = UniversalSystem()
    return _system


def get_capability_manager() -> SelfCapabilityManager:
    global _capability_manager
    if _capability_manager is None:
        _capability_manager = SelfCapabilityManager()
    return _capability_manager


OPENAPI_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "AnyClaw / CK-NEXUS MCP Server",
        "description": "เชื่อมต่อ ChatGPT กับ AnyClaw — สั่งงานจากแชท",
        "version": "1.0.0",
    },
    "servers": [{"url": "http://localhost:8765"}],
    "paths": {
        "/api/process": {
            "post": {
                "operationId": "processRequest",
                "summary": "ส่งคำขอให้ AnyClaw ประมวลผล",
                "description": "รับคำขอจาก ChatGPT → ประมวลผลผ่าน Universal System → ส่งผลลัพธ์กลับ",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "request": {
                                        "type": "string",
                                        "description": "คำขอที่ต้องการให้ประมวลผล",
                                    },
                                    "priority": {
                                        "type": "integer",
                                        "description": "ลำดับความสำคัญ (1=LOW, 2=NORMAL, 3=HIGH)",
                                        "default": 2,
                                    },
                                },
                                "required": ["request"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "ผลลัพธ์จากการประมวลผล",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "result": {"type": "string"},
                                        "duration": {"type": "number"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/capabilities": {
            "get": {
                "operationId": "getCapabilities",
                "summary": "ดูความสามารถทั้งหมดของ AnyClaw",
                "description": "แสดงรายการความสามารถทั้งหมดที่ AnyClaw ทำได้",
                "responses": {
                    "200": {
                        "description": "รายการความสามารถ",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "capabilities": {"type": "object"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/status": {
            "get": {
                "operationId": "getStatus",
                "summary": "ตรวจสอบสถานะระบบ AnyClaw",
                "description": "ดูสถานะของทุก subsystem",
                "responses": {
                    "200": {
                        "description": "สถานะระบบ",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "system": {"type": "object"},
                                        "uptime": {"type": "number"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/team": {
            "get": {
                "operationId": "getTeam",
                "summary": "ดูทีม AI ผู้เชี่ยวชาญ",
                "description": "แสดงรายชื่อและสถานะของ AI team members",
                "responses": {
                    "200": {
                        "description": "ข้อมูลทีม",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "team": {"type": "object"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/discover": {
            "post": {
                "operationId": "discoverCapabilities",
                "summary": "ค้นหาความสามารถใหม่",
                "description": "ค้นหาความสามารถใหม่จากแหล่งต่างๆ ทั่วโลก",
                "responses": {
                    "200": {
                        "description": "ผลลัพธ์การค้นหา",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "discovery": {"type": "object"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    """HTTPRequest handler สำหรับ MCP Server."""

    start_time = time.time()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/openapi.json":
            self._json_response(200, OPENAPI_SCHEMA)

        elif path == "/api/status":
            system = get_system()
            self._json_response(
                200,
                {
                    "status": "running",
                    "system": system.status(),
                    "uptime": time.time() - self.start_time,
                    "timestamp": time.time(),
                },
            )

        elif path == "/api/capabilities":
            manager = get_capability_manager()
            self._json_response(
                200,
                {
                    "status": "ok",
                    "capabilities": manager._capabilities,
                    "total": len(manager._capabilities),
                },
            )

        elif path == "/api/team":
            system = get_system()
            self._json_response(
                200,
                {
                    "status": "ok",
                    "team": system.team.list_team(),
                },
            )

        elif path == "/":
            self._json_response(
                200,
                {
                    "name": "AnyClaw MCP Server",
                    "version": "1.0.0",
                    "status": "running",
                    "endpoints": [
                        "POST /api/process — ส่งคำขอประมวลผล",
                        "GET /api/capabilities — ดูความสามารถ",
                        "GET /api/status — สถานะระบบ",
                        "GET /api/team — ทีม AI",
                        "POST /api/discover — ค้นหาความสามารถใหม่",
                        "GET /openapi.json — OpenAPI Schema สำหรับ ChatGPT",
                    ],
                },
            )

        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}

        if path == "/api/process":
            request_text = body.get("request", "")
            priority = body.get("priority", 2)
            start = time.time()

            system = get_system()
            result = system.process(request_text, priority=priority)

            self._json_response(
                200,
                {
                    "status": "completed",
                    "result": result,
                    "duration": time.time() - start,
                },
            )

        elif path == "/api/discover":
            manager = get_capability_manager()
            discovery = manager.discover_new_capabilities()
            self._json_response(
                200,
                {
                    "status": "ok",
                    "discovery": discovery,
                },
            )

        else:
            self._json_response(404, {"error": "Not found"})

    def _json_response(self, code: int, data: dict) -> None:
        response = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: Any) -> None:
        """Custom log format."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}" if args else "")


def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    """รัน MCP Server."""
    server = HTTPServer((host, port), MCPHandler)
    print(f"🚀 AnyClaw MCP Server running on http://{host}:{port}")
    print(f"📡 OpenAPI Schema: http://localhost:{port}/openapi.json")
    print(f"🔧 ChatGPT Actions URL: http://localhost:{port}/openapi.json")
    print("")
    print("วิธีเชื่อม ChatGPT:")
    print("  1. ไปที่ ChatGPT → Settings → Beta features → Custom GPTs → Actions")
    print("  2. กด Create new action → Import from URL")
    print(f"  3. ใส่: http://localhost:{port}/openapi.json")
    print("  4. Authentication: Bearer Token")
    print("  5. กด Save → เรียกใช้จากแชทได้เลย!")
    print("")
    print("📡 กด Ctrl+C เพื่อหยุด")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.server_close()


if __name__ == "__main__":
    run_server()
