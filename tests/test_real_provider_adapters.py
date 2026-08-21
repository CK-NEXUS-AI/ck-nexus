from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.real_provider_adapters import (
    ProviderBoundaryViolation,
    build_real_provider_adapter,
    probe_provider,
)


@dataclass
class FakeResponse:
    payload: dict

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class CaptureOpener:
    def __init__(self, payload: dict):
        self.payload = payload
        self.requests = []

    def __call__(self, request, timeout=0):
        self.requests.append((request, timeout))
        return FakeResponse(self.payload)


def broker_for(
    credential_id: CredentialId, value: str = "provider-secret"
) -> CredentialBroker:
    return CredentialBroker(environment={credential_id: value})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "credential_id", "payload", "expected"),
    [
        ("gemini", CredentialId.GEMINI_API_KEY, {"output_text": "G"}, "G"),
        (
            "anthropic",
            CredentialId.ANTHROPIC_API_KEY,
            {"content": [{"type": "text", "text": "A"}]},
            "A",
        ),
        ("groq", CredentialId.GROQ_API_KEY, {"output_text": "R"}, "R"),
        (
            "deepseek",
            CredentialId.DEEPSEEK_API_KEY,
            {"choices": [{"message": {"content": "D"}}]},
            "D",
        ),
        (
            "openrouter",
            CredentialId.OPENROUTER_API_KEY,
            {"choices": [{"message": {"content": "O"}}]},
            "O",
        ),
    ],
)
async def test_real_adapters_use_brokered_credentials(
    provider, credential_id, payload, expected
):
    opener = CaptureOpener(payload)
    adapter = build_real_provider_adapter(
        provider, broker_for(credential_id), model="test-model", opener=opener
    )
    assert adapter.is_available()
    assert await adapter.invoke("hello") == expected
    request, _ = opener.requests[0]
    assert "provider-secret" not in request.full_url
    assert adapter.capabilities.features >= {"text", "brokered-auth", "scoped-session"}


@pytest.mark.asyncio
async def test_gemini_uses_interactions_and_does_not_store_prompt_server_side():
    opener = CaptureOpener({"output_text": "OK"})
    adapter = build_real_provider_adapter(
        "gemini",
        broker_for(CredentialId.GEMINI_API_KEY),
        model="gemini-test",
        opener=opener,
    )
    await adapter.invoke("safe prompt")
    request, _ = opener.requests[0]
    body = json.loads(request.data.decode())
    assert request.full_url.endswith("/v1beta/interactions")
    assert body["store"] is False
    assert request.get_header("X-goog-api-key") == "provider-secret"


@pytest.mark.asyncio
async def test_anthropic_headers_and_messages_contract():
    opener = CaptureOpener({"content": [{"type": "text", "text": "OK"}]})
    adapter = build_real_provider_adapter(
        "anthropic",
        broker_for(CredentialId.ANTHROPIC_API_KEY),
        model="claude-test",
        opener=opener,
    )
    await adapter.invoke("safe prompt")
    request, _ = opener.requests[0]
    body = json.loads(request.data.decode())
    assert request.full_url == "https://api.anthropic.com/v1/messages"
    assert request.get_header("X-api-key") == "provider-secret"
    assert request.get_header("Anthropic-version") == "2023-06-01"
    assert body["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_boundary_rejects_credential_like_prompt_before_network():
    opener = CaptureOpener({"output_text": "should-not-run"})
    adapter = build_real_provider_adapter(
        "groq", broker_for(CredentialId.GROQ_API_KEY), model="groq-test", opener=opener
    )
    with pytest.raises(ProviderBoundaryViolation):
        await adapter.invoke("Bearer abcdefghijklmnopqrstuvwxyz.SECRET")
    assert opener.requests == []


@pytest.mark.asyncio
async def test_probe_returns_digest_not_raw_output():
    opener = CaptureOpener({"output_text": "OK"})
    adapter = build_real_provider_adapter(
        "groq", broker_for(CredentialId.GROQ_API_KEY), model="groq-test", opener=opener
    )
    evidence = await probe_provider(adapter)
    data = evidence.as_dict()
    assert data["success"] is True
    assert data["output_digest"]
    assert data["raw_output_stored"] is False
    assert "OK" not in json.dumps(data)


def test_unknown_provider_fails_closed():
    with pytest.raises(ValueError):
        build_real_provider_adapter("unknown", CredentialBroker(), model="x")


def test_real_adapter_binds_only_to_matching_verified_descriptor():
    from creator_app.provider_onboarding import (
        ProviderOnboardingRegistry,
        default_provider_catalog,
    )

    r = ProviderOnboardingRegistry(default_provider_catalog())
    r.authorize("groq", evidence_ref="auth:1")
    r.verify("groq", evidence_ref="probe:1")
    adapter = build_real_provider_adapter(
        "groq",
        broker_for(CredentialId.GROQ_API_KEY),
        model="groq-test",
        opener=CaptureOpener({"output_text": "OK"}),
    )
    assert r.bind_adapter("groq", adapter) is adapter


def test_provider_router_includes_only_explicitly_configured_extra_models():
    from creator_app.config import Settings
    from creator_app.providers import build_provider_router

    b = CredentialBroker(environment={CredentialId.GROQ_API_KEY: "provider-secret"})
    router = build_provider_router(Settings(openai_model="", groq_model="groq-test"), b)
    names = {s.name for s in router.statuses()}
    assert "groq" in names
    assert "gemini" not in names
    assert "anthropic" not in names
