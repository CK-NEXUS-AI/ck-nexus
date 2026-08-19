"""Unit tests for free provider adapters — no live API keys needed."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creator_app.free_providers import (
    GeminiAdapter,
    OpenAICompatibleAdapter,
    QuotaTracker,
    build_free_adapters,
)
from creator_app.provider_router import ProviderKind

# ── QuotaTracker Tests ──────────────────────────────────────────────────────


class TestQuotaTracker:
    def test_record_increments(self):
        qt = QuotaTracker()
        qt.record("groq", tokens=100)
        qt.record("groq", tokens=200)
        stats = qt.stats("groq")
        assert stats["requests"] == 2
        assert stats["tokens"] == 300

    def test_rate_limit_detection(self):
        qt = QuotaTracker()
        qt.record_error("groq", "HTTP 429 Too Many Requests")
        assert qt.is_rate_limited("groq") is True

    def test_rate_limit_expires(self):
        qt = QuotaTracker(windows_seconds=0.1)
        qt.record_error("groq", "HTTP 429")
        assert qt.is_rate_limited("groq") is True
        time.sleep(0.15)
        assert qt.is_rate_limited("groq") is False

    def test_window_reset(self):
        qt = QuotaTracker(windows_seconds=0.05)
        qt.record("groq", tokens=100)
        time.sleep(0.1)
        qt.record("groq", tokens=50)
        stats = qt.stats("groq")
        assert stats["requests"] == 1
        assert stats["tokens"] == 50


# ── OpenAICompatibleAdapter Tests ───────────────────────────────────────────


class TestOpenAICompatibleAdapter:
    def test_not_available_without_key(self):
        adapter = OpenAICompatibleAdapter(
            name="test",
            base_url="http://x",
            env_key="NONEXISTENT_KEY_XYZ",
            model="test-model",
        )
        assert adapter.is_available() is False

    def test_available_with_key(self):
        with patch.dict(os.environ, {"TEST_PROVIDER_KEY": "sk-test123"}):
            adapter = OpenAICompatibleAdapter(
                name="test",
                base_url="http://localhost:8080",
                env_key="TEST_PROVIDER_KEY",
                model="test-model",
            )
            assert adapter.is_available() is True

    def test_not_available_when_rate_limited(self):
        qt = QuotaTracker()
        qt.record_error("test", "HTTP 429 rate limited")
        with patch.dict(os.environ, {"TEST_KEY": "sk-123"}):
            adapter = OpenAICompatibleAdapter(
                name="test",
                base_url="http://x",
                env_key="TEST_KEY",
                model="m",
                quota_tracker=qt,
            )
            assert adapter.is_available() is False

    def test_capabilities(self):
        adapter = OpenAICompatibleAdapter(
            name="groq",
            base_url="http://x",
            env_key="K",
            model="llama-3.3-70b",
            models=("llama-3.3-70b", "llama-3.1-8b"),
            features=frozenset({"text", "fast"}),
        )
        assert adapter.kind == ProviderKind.CLOUD
        assert adapter.capabilities.supports(["text"]) is True
        assert adapter.capabilities.supports(["fast"]) is True
        assert adapter.capabilities.supports(["missing"]) is False

    def test_invoke_success(self):
        mock_response = json.dumps(
            {
                "choices": [{"message": {"content": "Hello world"}}],
                "usage": {"total_tokens": 50},
            }
        ).encode()

        mock_urlopen = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with patch.dict(os.environ, {"TEST_KEY": "sk-test"}):
            OpenAICompatibleAdapter(
                name="test",
                base_url="http://localhost",
                env_key="TEST_KEY",
                model="m",
                opener=mock_urlopen,
            )
            # Need to pass opener to __init__ — but our adapter uses urlopen directly
            # Test via the _call path
            from creator_app.free_providers import OpenAICompatibleAdapter as OCA

            qt = QuotaTracker()
            adapter2 = OCA(
                name="test",
                base_url="http://localhost",
                env_key="TEST_KEY",
                model="m",
                quota_tracker=qt,
            )
            # Patch urlopen at module level
            with patch("creator_app.free_providers.urlopen", mock_urlopen):
                result = asyncio.run(adapter2.invoke("Hi"))
            assert result == "Hello world"
            assert qt.stats("test")["tokens"] == 50

    def test_invoke_raises_on_empty_response(self):
        mock_response = json.dumps(
            {
                "choices": [{"message": {"content": ""}}],
                "usage": {},
            }
        ).encode()

        mock_urlopen = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with patch.dict(os.environ, {"TEST_KEY": "sk-test"}):
            adapter = OpenAICompatibleAdapter(
                name="test",
                base_url="http://localhost",
                env_key="TEST_KEY",
                model="m",
            )
            with patch("creator_app.free_providers.urlopen", mock_urlopen):
                try:
                    asyncio.run(adapter.invoke("Hi"))
                    raise AssertionError("Should have raised")
                except RuntimeError as e:
                    assert "empty" in str(e).lower()


# ── GeminiAdapter Tests ─────────────────────────────────────────────────────


class TestGeminiAdapter:
    def test_not_available_without_key(self):
        adapter = GeminiAdapter()
        assert adapter.is_available() is False

    def test_capabilities(self):
        adapter = GeminiAdapter(model="gemini-2.0-flash")
        assert adapter.kind == ProviderKind.CLOUD
        assert adapter.capabilities.supports(["vision"]) is True
        assert "gemini-2.0-flash" in adapter.capabilities.models


# ── build_free_adapters Tests ───────────────────────────────────────────────


class TestBuildFreeAdapters:
    def test_empty_without_keys(self):
        adapters = build_free_adapters()
        assert len(adapters) == 0

    def test_builds_groq_when_key_set(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}):
            adapters = build_free_adapters()
            names = [a.name for a in adapters]
            assert "groq" in names

    def test_builds_multiple_providers(self):
        env = {
            "GROQ_API_KEY": "gsk_test",
            "GEMINI_API_KEY": "AIza_test",
            "DEEPSEEK_API_KEY": "sk_test",
        }
        with patch.dict(os.environ, env, clear=False):
            adapters = build_free_adapters()
            names = [a.name for a in adapters]
            assert "groq" in names
            assert "gemini" in names
            assert "deepseek" in names

    def test_shared_quota_tracker(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}):
            qt = QuotaTracker()
            adapters = build_free_adapters(quota_tracker=qt)
            assert len(adapters) >= 1
            # Record on adapter's tracker should reflect in shared tracker
            adapters[0]._quota.record("groq", tokens=100)
            assert qt.stats("groq")["tokens"] == 100
