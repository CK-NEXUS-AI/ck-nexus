from __future__ import annotations

from creator_app.telegram_bridge import TelegramBridge, TelegramBridgeConfig


def test_whoami_is_available_before_allowlist() -> None:
    calls: list[tuple[str, dict | None, dict | None]] = []

    def fake(url, payload=None, headers=None):
        calls.append((url, payload, headers))
        return {"ok": True}

    bridge = TelegramBridge(TelegramBridgeConfig(bot_token="test-token"), fake)
    bridge.handle_message({"chat": {"id": 123}, "text": "/whoami"})

    assert calls[-1][1]["chat_id"] == 123
    assert "chat_id=123" in calls[-1][1]["text"]


def test_unknown_chat_fails_closed() -> None:
    calls = []

    def fake(url, payload=None, headers=None):
        calls.append((url, payload, headers))
        return {"ok": True}

    bridge = TelegramBridge(TelegramBridgeConfig(bot_token="test-token"), fake)
    bridge.handle_message({"chat": {"id": 999}, "text": "/status"})

    assert "BLOCKED" in calls[-1][1]["text"]
    assert not any("/api/status" in call[0] for call in calls)


def test_status_routes_to_ck_api_for_allowed_chat() -> None:
    calls = []

    def fake(url, payload=None, headers=None):
        calls.append((url, payload, headers))
        if url.endswith("/api/status"):
            return {
                "name": "CK-NEXUS",
                "version": "dev",
                "mode": "mock",
                "model": "mock",
                "database_ready": True,
                "access_required": True,
            }
        return {"ok": True}

    config = TelegramBridgeConfig(bot_token="test-token", allowed_chat_ids=frozenset({123}))
    bridge = TelegramBridge(config, fake)
    bridge.handle_message({"chat": {"id": 123}, "text": "/status"})

    assert any(call[0].endswith("/api/status") for call in calls)
    assert "database_ready=True" in calls[-1][1]["text"]


def test_ask_requires_ck_access_token() -> None:
    calls = []

    def fake(url, payload=None, headers=None):
        calls.append((url, payload, headers))
        return {"ok": True}

    config = TelegramBridgeConfig(bot_token="test-token", allowed_chat_ids=frozenset({123}))
    bridge = TelegramBridge(config, fake)
    bridge.handle_message({"chat": {"id": 123}, "text": "/ask ทดสอบระบบ"})

    assert "BLOCKED" in calls[-1][1]["text"]
    assert not any("/api/runs" in call[0] for call in calls)


def test_ask_routes_with_bearer_token() -> None:
    calls = []

    def fake(url, payload=None, headers=None):
        calls.append((url, payload, headers))
        if url.endswith("/api/runs"):
            return {"content": "ผ่าน"}
        return {"ok": True}

    config = TelegramBridgeConfig(
        bot_token="test-token",
        ck_access_token="access-test",
        allowed_chat_ids=frozenset({123}),
        default_agent_id="general",
    )
    bridge = TelegramBridge(config, fake)
    bridge.handle_message({"chat": {"id": 123}, "text": "/ask ทดสอบระบบ"})

    run_call = next(call for call in calls if call[0].endswith("/api/runs"))
    assert run_call[1]["session_id"] == "telegram:123"
    assert run_call[2]["Authorization"] == "Bearer access-test"
    assert calls[-1][1]["text"] == "ผ่าน"
