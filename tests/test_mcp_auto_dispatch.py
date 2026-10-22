from __future__ import annotations

from typing import Any

import creator_app.agnes.mcp_server as mcp_server


class FakeSystem:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def process(self, request: str, *, priority: int = 2) -> str:
        self.calls.append((request, priority))
        return "PLAN-ONLY"


class FakeReplyPlugin:
    def reply(self, request: str, *, max_tokens: int = 512) -> dict[str, Any]:
        return {
            "ok": True,
            "provider": "mock-provider",
            "model": "mock-model",
            "response": f"answer:{request}",
            "latency_ms": 1,
            "attempts": 1,
            "fallback_used": False,
        }


def test_auto_dispatch_routes_development_request_to_plan_only(monkeypatch):
    system = FakeSystem()
    monkeypatch.setattr(mcp_server, "get_system", lambda: system)

    result = mcp_server.cknexus_auto_dispatch("ช่วยแก้โค้ดใน repo", priority=3)

    assert result["ok"] is True
    assert result["mode"] == "plan"
    assert result["execution_state"] == "PLANNED_NOT_EXECUTED"
    assert result["external_mutation_authorized"] is False
    assert result["release_evidence"] is False
    assert system.calls == [("ช่วยแก้โค้ดใน repo", 3)]


def test_auto_dispatch_recognizes_short_thai_continuation_commands(monkeypatch):
    system = FakeSystem()
    monkeypatch.setattr(mcp_server, "get_system", lambda: system)

    result = mcp_server.cknexus_auto_dispatch("ลุยต่อ")

    assert result["mode"] == "plan"
    assert result["execution_state"] == "PLANNED_NOT_EXECUTED"
    assert system.calls == [("ลุยต่อ", 2)]


def test_auto_dispatch_routes_normal_question_to_configured_provider(monkeypatch):
    monkeypatch.setattr(mcp_server, "AutoReplyPlugin", FakeReplyPlugin)

    result = mcp_server.cknexus_auto_dispatch("อธิบาย MCP แบบสั้น")

    assert result["ok"] is True
    assert result["mode"] == "answer"
    assert result["execution_state"] == "ANSWER_RETURNED"
    assert result["response"] == "answer:อธิบาย MCP แบบสั้น"
    assert result["provider"] == "mock-provider"


def test_auto_dispatch_explicit_plan_does_not_call_model(monkeypatch):
    system = FakeSystem()
    monkeypatch.setattr(mcp_server, "get_system", lambda: system)

    result = mcp_server.cknexus_auto_dispatch("question", mode="plan")

    assert result["mode"] == "plan"
    assert result["plan"] == "PLAN-ONLY"
    assert system.calls == [("question", 2)]


def test_auto_dispatch_returns_safe_provider_error(monkeypatch):
    class BrokenPlugin:
        def reply(self, request: str, *, max_tokens: int = 512) -> dict[str, Any]:
            raise mcp_server.AutoReplyError("NO_PROVIDER_CONFIGURED", "No provider configured.")

    monkeypatch.setattr(mcp_server, "AutoReplyPlugin", BrokenPlugin)
    result = mcp_server.cknexus_auto_dispatch("hello", mode="answer")

    assert result["ok"] is False
    assert result["error_code"] == "NO_PROVIDER_CONFIGURED"
    assert result["execution_state"] == "NOT_EXECUTED"
    assert result["secret_values_exposed"] is False


def test_auto_dispatch_rejects_invalid_mode_priority_and_empty_request():
    assert mcp_server.cknexus_auto_dispatch("hello", mode="unsafe")["error_code"] == "INVALID_MODE"
    assert mcp_server.cknexus_auto_dispatch("hello", priority=4)["error_code"] == "INVALID_PRIORITY"
    assert mcp_server.cknexus_auto_dispatch("   ")["error_code"] == "EMPTY_REQUEST"
