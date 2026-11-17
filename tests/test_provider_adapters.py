from __future__ import annotations

from types import SimpleNamespace

import pytest

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.providers import (
    ClaudeProviderAdapter,
    OllamaProviderAdapter,
    OpenAIProviderAdapter,
    UnsafeLocalProviderUrl,
    validate_loopback_base_url,
)


def test_ollama_base_url_is_loopback_only() -> None:
    assert validate_loopback_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert validate_loopback_base_url("http://localhost:11434/") == "http://localhost:11434"
    with pytest.raises(UnsafeLocalProviderUrl):
        validate_loopback_base_url("https://example.com")
    with pytest.raises(UnsafeLocalProviderUrl):
        validate_loopback_base_url("http://user:pass@127.0.0.1:11434")


def test_ollama_requires_enablement_and_model() -> None:
    disabled = OllamaProviderAdapter(
        base_url="http://127.0.0.1:11434", model="gemma3", enabled=False
    )
    missing_model = OllamaProviderAdapter(base_url="http://127.0.0.1:11434", model="", enabled=True)
    assert disabled.is_available() is False
    assert missing_model.is_available() is False


@pytest.mark.asyncio
async def test_openai_adapter_uses_broker_without_exposing_key() -> None:
    broker = CredentialBroker(environment={CredentialId.OPENAI_API_KEY: "sk-provider-secret"})
    captured = {}

    class Responses:
        async def create(self, *, model, input):
            captured["model"] = model
            captured["input"] = input
            return SimpleNamespace(output_text="provider result")

    class Client:
        def __init__(self):
            self.responses = Responses()

    def factory(**kwargs):
        captured["api_key"] = kwargs["api_key"]
        return Client()

    adapter = OpenAIProviderAdapter(broker, model="gpt-test", client_factory=factory)
    assert adapter.is_available() is True
    result = await adapter.invoke("hello")
    assert result == "provider result"
    assert captured["api_key"] == "sk-provider-secret"
    assert "sk-provider-secret" not in repr(adapter.__dict__)


def test_paid_openai_adapter_is_disabled_in_free_only_mode(monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_FREE_ONLY", "true")
    broker = CredentialBroker(environment={CredentialId.OPENAI_API_KEY: "sk-test"})
    adapter = OpenAIProviderAdapter(broker, model="gpt-test")
    assert adapter.is_available() is False


@pytest.mark.asyncio
async def test_claude_adapter_uses_messages_api_and_keeps_key_out_of_adapter(monkeypatch) -> None:
    import json
    from io import BytesIO

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-claude-secret")
    captured = {}

    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response(json.dumps({
            "content": [{"type": "text", "text": "claude test response"}]
        }).encode("utf-8"))

    adapter = ClaudeProviderAdapter(opener=opener)
    assert adapter.is_available()
    assert await adapter.invoke("hello") == "claude test response"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["body"]["model"] == "claude-sonnet-4-5"
    assert captured["headers"]["X-api-key"] == "test-claude-secret"
    assert "test-claude-secret" not in repr(adapter.__dict__)
