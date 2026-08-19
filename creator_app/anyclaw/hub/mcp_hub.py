"""MCP Hub — Central Hub สำหรับ Agent ทั้งหมด.

เชื่อมต่อ Codex, Claude Code, Ollama, OpenClaw, Gemini
เป็น single endpoint ที่ทุก agent คุยกันได้

วิธีใช้:
    hub = MCPHub()
    hub.register_agent("codex", CodexTool())
    hub.register_agent("claude", ClaudeTool())

    # เรียกใช้ agent ใดก็ได้
    result = hub.call("codex", "สร้าง API endpoint")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AgentTool:
    """เครื่องมือของ agent หนึ่งตัว."""

    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class AgentEndpoint:
    """endpoint ของ agent หนึ่งตัว."""

    name: str
    display_name: str
    tools: list[AgentTool] = field(default_factory=list)
    available: bool = False
    last_call: float = 0.0
    call_count: int = 0


class MCPHub:
    """Central Hub — เชื่อมทุก Agent.

    วิธีใช้:
        hub = MCPHub()

        # ลงทะเบียน agents
        hub.register("codex", "Codex CLI", tools=[
            AgentTool("code_generate", "สร้างโค้ด"),
            AgentTool("code_review", "ตรวจโค้ด"),
        ])
        hub.register("claude", "Claude Code", tools=[
            AgentTool("analyze", "วิเคราะห์"),
            AgentTool("refactor", "ปรับโครงสร้าง"),
        ])

        # ดู agents ทั้งหมด
        agents = hub.list_agents()

        # เรียกใช้
        result = hub.call_tool("codex", "code_generate", {"language": "python"})
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentEndpoint] = {}
        self._event_log: list[dict] = []

    def register(
        self,
        name: str,
        display_name: str,
        *,
        tools: list[AgentTool] | None = None,
    ) -> None:
        """ลงทะเบียน agent."""
        self._agents[name] = AgentEndpoint(
            name=name,
            display_name=display_name,
            tools=tools or [],
            available=True,
        )
        self._log("register", name)

    def unregister(self, name: str) -> bool:
        """ลบ agent."""
        if name in self._agents:
            del self._agents[name]
            self._log("unregister", name)
            return True
        return False

    def list_agents(self) -> list[dict]:
        """ดู agents ทั้งหมด."""
        return [
            {
                "name": a.name,
                "display_name": a.display_name,
                "available": a.available,
                "tools": [t.name for t in a.tools],
                "call_count": a.call_count,
            }
            for a in self._agents.values()
        ]

    def get_tools(self, agent_name: str | None = None) -> list[dict]:
        """ดู tools ทั้งหมด."""
        tools = []
        agents = [self._agents[agent_name]] if agent_name else self._agents.values()
        for agent in agents:
            for tool in agent.tools:
                tools.append({
                    "agent": agent.name,
                    "tool": tool.name,
                    "description": tool.description,
                })
        return tools

    def call_tool(
        self,
        agent_name: str,
        tool_name: str,
        params: dict | None = None,
    ) -> dict:
        """เรียกใช้ tool ของ agent."""
        agent = self._agents.get(agent_name)
        if not agent:
            return {"ok": False, "error": f"Agent {agent_name} not registered"}
        if not agent.available:
            return {"ok": False, "error": f"Agent {agent_name} not available"}

        tool = next((t for t in agent.tools if t.name == tool_name), None)
        if not tool:
            return {"ok": False, "error": f"Tool {tool_name} not found in {agent_name}"}

        agent.last_call = time.time()
        agent.call_count += 1
        self._log("call_tool", agent_name, f"{tool_name}({params})")

        return {
            "ok": True,
            "agent": agent_name,
            "tool": tool_name,
            "params": params,
            "status": "dispatched",
        }

    def find_tool(self, keyword: str) -> list[dict]:
        """ค้นหา tool ด้วย keyword."""
        results = []
        keyword_lower = keyword.lower()
        for agent in self._agents.values():
            for tool in agent.tools:
                if (keyword_lower in tool.name.lower()
                        or keyword_lower in tool.description.lower()):
                    results.append({
                        "agent": agent.name,
                        "tool": tool.name,
                        "description": tool.description,
                    })
        return results

    def status(self) -> dict:
        """สถานะ hub."""
        available = sum(1 for a in self._agents.values() if a.available)
        total_tools = sum(len(a.tools) for a in self._agents.values())
        return {
            "total_agents": len(self._agents),
            "available_agents": available,
            "total_tools": total_tools,
            "agents": {a.name: a.available for a in self._agents.values()},
        }

    def _log(self, event: str, agent: str, detail: str = "") -> None:
        self._event_log.append({
            "event": event,
            "agent": agent,
            "detail": detail,
            "timestamp": time.time(),
        })

    @property
    def events(self) -> list[dict]:
        return list(self._event_log)
