"""Tests — Agent Bridge + MCP Hub + Skills Summary."""

from __future__ import annotations

from creator_app.anyclaw.bridge.agent_registry import AgentRegistry
from creator_app.anyclaw.bridge.local_model_bridge import LocalModelBridge
from creator_app.anyclaw.hub.mcp_hub import AgentTool, MCPHub
from creator_app.anyclaw.skills_summary import SkillsSummary


class TestAgentRegistry:
    def test_scan(self):
        reg = AgentRegistry()
        agents = reg.scan()
        assert len(agents) >= 5

    def test_get_available(self):
        reg = AgentRegistry()
        reg.scan()
        available = reg.get_available()
        for a in available:
            assert a.available is True

    def test_status(self):
        reg = AgentRegistry()
        reg.scan()
        status = reg.status()
        assert "total_agents" in status
        assert status["total_agents"] >= 5

    def test_get_by_category(self):
        reg = AgentRegistry()
        reg.scan()
        runtimes = reg.get_by_category("runtime")
        assert len(runtimes) >= 1


class TestLocalModelBridge:
    def test_discover(self):
        bridge = LocalModelBridge()
        models = bridge.discover()
        assert isinstance(models, list)

    def test_status(self):
        bridge = LocalModelBridge()
        bridge.discover()
        status = bridge.status()
        assert "total_models" in status


class TestMCPHub:
    def test_register_and_list(self):
        hub = MCPHub()
        hub.register("codex", "Codex CLI", tools=[
            AgentTool("code_gen", "สร้างโค้ด"),
        ])
        agents = hub.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "codex"

    def test_call_tool(self):
        hub = MCPHub()
        hub.register("test", "Test Agent", tools=[
            AgentTool("do_something", "ทำอะไรสักอย่าง"),
        ])
        result = hub.call_tool("test", "do_something", {"param": "value"})
        assert result["ok"] is True

    def test_call_tool_not_found(self):
        hub = MCPHub()
        hub.register("test", "Test Agent")
        result = hub.call_tool("test", "nonexistent")
        assert result["ok"] is False

    def test_find_tool(self):
        hub = MCPHub()
        hub.register("a", "Agent A", tools=[
            AgentTool("security_scan", "สแกนความปลอดภัย"),
            AgentTool("code_gen", "สร้างโค้ด"),
        ])
        results = hub.find_tool("security")
        assert len(results) == 1
        assert results[0]["tool"] == "security_scan"

    def test_status(self):
        hub = MCPHub()
        hub.register("x", "X Agent", tools=[AgentTool("t1", "tool 1")])
        hub.register("y", "Y Agent", tools=[AgentTool("t2", "tool 2")])
        status = hub.status()
        assert status["total_agents"] == 2
        assert status["total_tools"] == 2


class TestSkillsSummary:
    def test_full_report(self):
        summary = SkillsSummary()
        report = summary.full_report()
        assert "CK-NEXUS" in report
        assert "Codex" in report

    def test_by_category(self):
        summary = SkillsSummary()
        core = summary.by_category("core")
        assert len(core) >= 4

    def test_search(self):
        summary = SkillsSummary()
        results = summary.search("security")
        assert len(results) >= 3

    def test_categories(self):
        summary = SkillsSummary()
        cats = summary.categories()
        assert "core" in cats
        assert cats["core"] >= 4
