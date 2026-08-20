"""AnyClaw MCP Server — เชื่อมต่อกับ GPT ได้ทันที.

วิธีใช้:
    python -m creator_app.anyclaw.mcp_server_gpt
    
GPT จะเห็น tools:
    - anyclaw_chat: คุยกับ AnyClaw AI
    - anyclaw_search: ค้นหาข้อมูล
    - anyclaw_tts: สร้างเสียง
    - anyclaw_hub_status: ดูสถานะ USB Hub
    - anyclaw_failover: ทดสอบ failover
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from creator_app.anyclaw.core import AnyClawCore
from creator_app.anyclaw.hub.usb_hub import USBHub

class AnyClawMCPServer:
    def __init__(self):
        self.claw = AnyClawCore(mode="super")
        self.tools = [
            {
                "name": "anyclaw_chat",
                "description": "คุยกับ AnyClaw AI — ใช้ USB Hub auto-select best provider",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "ข้อความที่ต้องการส่ง"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "anyclaw_search",
                "description": "ค้นหาข้อมูลผ่าน USB Hub (DuckDuckGo)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "คำค้นหา"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "anyclaw_tts",
                "description": "สร้างเสียงภาษาไทยจากข้อความ",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "ข้อความที่ต้องการเปลี่ยนเป็นเสียง"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "anyclaw_hub_status",
                "description": "ดูสถานะ USB Hub — พอร์ตทั้งหมด, provider ที่ใช้งาน",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "anyclaw_failover",
                "description": "ทดสอบ failover — จำลอง provider ล้มแล้วดูการสลับ",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {"type": "string", "description": "ชื่อ provider ที่ต้องการ kill"}
                    }
                }
            }
        ]

    def handle(self, method: str, params: dict) -> dict:
        if method == "tools/list":
            return {"tools": self.tools}
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            return self._call_tool(name, args)
        return {"error": f"Unknown method: {method}"}

    def _call_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "anyclaw_chat":
                resp = self.claw.hub_chat(args.get("message", ""))
                return {"content": [{"type": "text", "text": f"Provider: {resp.provider}\nResponse: {resp.content}"}]}
            elif name == "anyclaw_search":
                resp = self.claw.hub_search(args.get("query", ""))
                results = resp.get("response", [])
                text = "\n".join([f"{i+1}. {r.get('title', 'N/A')}" for i, r in enumerate(results[:3])]) if isinstance(results, list) else str(results)
                return {"content": [{"type": "text", "text": f"Provider: {resp.get('provider')}\n{text}"}]}
            elif name == "anyclaw_tts":
                resp = self.claw.hub_tts(args.get("text", ""), output="/tmp/mcp_tts.mp3")
                return {"content": [{"type": "text", "text": f"Provider: {resp.get('provider')}\nFile: {resp.get('response')}"}]}
            elif name == "anyclaw_hub_status":
                status = self.claw.hub_status()
                text = json.dumps(status, indent=2)
                return {"content": [{"type": "text", "text": text}]}
            elif name == "anyclaw_failover":
                provider = args.get("provider", "groq_free")
                slot = self.claw._hub.get_best_slot("llm")
                if slot and slot.provider_name == provider:
                    slot.consecutive_errors = 3
                    slot.status = "error"
                resp = self.claw.hub_chat("failover test")
                return {"content": [{"type": "text", "text": f"Failover: {provider} -> {resp.provider}"}]}
            return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            return {"error": str(e)}

def main():
    server = AnyClawMCPServer()
    print("AnyClaw MCP Server — Ready for GPT")
    print("Tools available:", [t["name"] for t in server.tools])
    print()
    print("To connect GPT:")
    print("1. Open ChatGPT")
    print("2. Go to Settings > Plugins > Install")
    print("3. Use this server URL")
    print()
    print("Or test directly:")
    result = server.handle("tools/call", {"name": "anyclaw_chat", "arguments": {"message": "สวัสดีครับ"}})
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
