"""Tests สำหรับ AnyClaw Core."""

from __future__ import annotations

from unittest.mock import patch

from creator_app.anyclaw.core import AnyClawCore, ChatResponse


class TestAnyClawCore:
    def test_init(self):
        claw = AnyClawCore(mode="super")
        assert claw.mode == "super"

    def test_status(self):
        claw = AnyClawCore()
        status = claw.status()
        assert "mode" in status
        assert "cache_size" in status
        assert "free_providers_available" in status

    def test_cache_hit(self):
        claw = AnyClawCore(mode="free")
        with patch.object(claw, "_try_free_providers") as mock_free:
            mock_free.return_value = ChatResponse(
                content="cached response", provider="test",
            )
            claw.chat("hello")
            resp2 = claw.chat("hello")
            assert resp2.from_cache is True
            assert resp2.content == "cached response"
            assert mock_free.call_count == 1

    def test_clear_cache(self):
        claw = AnyClawCore()
        claw._cache["key"] = "value"
        claw.clear_cache()
        assert len(claw._cache) == 0

    def test_chat_response(self):
        r = ChatResponse(content="hi", provider="p", model="m")
        assert r.from_cache is False
        assert r.tokens_used == 0

    def test_call_count_tracking(self):
        claw = AnyClawCore(mode="free")
        with patch.object(claw, "_try_free_providers") as mock_free:
            mock_free.return_value = ChatResponse(
                content="ok", provider="groq",
            )
            claw.chat("a")
            claw.chat("b")
            assert claw._call_count.get("groq", 0) == 2
