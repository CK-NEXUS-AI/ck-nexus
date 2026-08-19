"""Tests — Architecture Layers: Core + Adapters + Storage."""

from __future__ import annotations

import tempfile

import pytest

from creator_app.core.policy_engine import ActionType, PolicyDecision, PolicyEngine
from creator_app.core.state_manager import StateManager
from creator_app.connectors.providers.base import ProviderAdapter, ProviderResponse
from creator_app.connectors.channels.webhook_connector import WebhookConnector
from creator_app.storage.sdcard_manager import SDCardManager


class TestPolicyEngine:
    def test_check_permission_allow(self):
        engine = PolicyEngine()
        result = engine.check_permission(ActionType.READ, "gmail")
        assert result.decision == PolicyDecision.ALLOW

    def test_check_permission_approval(self):
        engine = PolicyEngine()
        result = engine.check_permission(ActionType.EXECUTE, "shell")
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL

    def test_log_action(self):
        engine = PolicyEngine()
        engine.log_action("read_email", "user", "gmail", evidence="3 ฉบับ")
        trail = engine.get_audit_trail()
        assert len(trail) == 1
        assert trail[0]["action"] == "read_email"

    def test_add_policy(self):
        engine = PolicyEngine()
        engine.add_policy(ActionType.DEPLOY, "vercel", PolicyDecision.ALLOW)
        result = engine.check_permission(ActionType.DEPLOY, "vercel")
        assert result.decision == PolicyDecision.ALLOW

    def test_stats(self):
        engine = PolicyEngine()
        engine.log_action("a1", "u", "r")
        engine.log_action("a2", "u", "r")
        stats = engine.stats()
        assert stats["total_actions"] == 2


class TestStateManager:
    def test_set_and_get(self):
        with tempfile.TemporaryDirectory() as d:
            sm = StateManager(state_dir=d)
            sm.set("key1", "value1")
            assert sm.get("key1") == "value1"

    def test_version_increment(self):
        with tempfile.TemporaryDirectory() as d:
            sm = StateManager(state_dir=d)
            sm.set("k", "v1")
            sm.set("k", "v2")
            assert sm.get("k") == "v2"
            history = sm.history("k")
            assert len(history) == 2

    def test_delete(self):
        with tempfile.TemporaryDirectory() as d:
            sm = StateManager(state_dir=d)
            sm.set("k", "v")
            assert sm.delete("k")
            assert sm.get("k") is None

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as d:
            sm = StateManager(state_dir=d)
            sm.set("a", 1, category="cat1")
            sm.set("b", 2, category="cat2")
            assert "a" in sm.list_keys("cat1")
            assert "b" not in sm.list_keys("cat1")

    def test_stats(self):
        with tempfile.TemporaryDirectory() as d:
            sm = StateManager(state_dir=d)
            sm.set("x", 10)
            stats = sm.stats()
            assert stats["total_keys"] == 1


class TestProviderAdapters:
    def test_base_interface(self):
        assert hasattr(ProviderAdapter, "name")
        assert hasattr(ProviderAdapter, "env_key")
        assert hasattr(ProviderAdapter, "chat")

    def test_response_dataclass(self):
        r = ProviderResponse(content="hi", model="m", provider="p")
        assert r.success is True
        assert r.content == "hi"

    def test_groq_adapter(self):
        from creator_app.connectors.providers.groq_adapter import GroqAdapter
        a = GroqAdapter()
        assert a.name == "groq"
        assert a.env_key == "GROQ_API_KEY"

    def test_openai_adapter(self):
        from creator_app.connectors.providers.openai_adapter import OpenAIAdapter
        a = OpenAIAdapter()
        assert a.name == "openai"

    def test_google_adapter(self):
        from creator_app.connectors.providers.google_adapter import GoogleAdapter
        a = GoogleAdapter()
        assert a.name == "google_ai"

    def test_ollama_adapter(self):
        from creator_app.connectors.providers.ollama_adapter import OllamaAdapter
        a = OllamaAdapter()
        assert a.name == "ollama"


class TestWebhookConnector:
    def test_receive_valid(self):
        wh = WebhookConnector()
        payload = wh.receive({}, '{"event": "test"}')
        assert payload == {"event": "test"}
        assert wh.received_count == 1

    def test_receive_invalid_json(self):
        wh = WebhookConnector()
        payload = wh.receive({}, "not json")
        assert payload is None

    def test_secret_verification(self):
        wh = WebhookConnector(secret="mysecret")
        body = '{"test": true}'
        import hashlib
        sig = "sha256=" + hashlib.sha256(("mysecret" + body).encode()).hexdigest()
        payload = wh.receive({"X-Hub-Signature-256": sig}, body)
        assert payload is not None

    def test_secret_verification_fail(self):
        wh = WebhookConnector(secret="mysecret")
        payload = wh.receive({"X-Hub-Signature-256": "wrong"}, '{"test": true}')
        assert payload is None


class TestSDCardManager:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            mgr = SDCardManager(base_path=d)
            mgr.save("logs", "2024-01", {"events": ["a", "b"]})
            data = mgr.load("logs", "2024-01")
            assert data["events"] == ["a", "b"]

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as d:
            mgr = SDCardManager(base_path=d)
            mgr.save("ns", "k1", "a")
            mgr.save("ns", "k2", "b")
            keys = mgr.list_keys("ns")
            assert "k1" in keys
            assert "k2" in keys

    def test_delete(self):
        with tempfile.TemporaryDirectory() as d:
            mgr = SDCardManager(base_path=d)
            mgr.save("ns", "k", "v")
            assert mgr.delete("ns", "k")
            assert mgr.load("ns", "k") is None

    def test_stats(self):
        with tempfile.TemporaryDirectory() as d:
            mgr = SDCardManager(base_path=d)
            mgr.save("ns", "k", "v")
            stats = mgr.stats()
            assert stats["total_namespaces"] >= 1
