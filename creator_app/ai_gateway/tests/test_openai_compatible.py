import pytest

from creator_app.ai_gateway import (
    ModelCapability,
    ModelDescriptor,
    OpenAICompatibleEndpoint,
    OpenAICompatibleProviderAdapter,
)


def _model(provider_id: str, runtime_id: str = "openai-compatible") -> ModelDescriptor:
    return ModelDescriptor(
        provider_id,
        "model-a",
        frozenset({ModelCapability.TEXT}),
        runtime_id=runtime_id,
    )


def test_remote_endpoint_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        OpenAICompatibleEndpoint(
            provider_id="remote",
            base_url="http://example.com/v1",
            credential_ref="broker://remote/api-key",
        )


def test_endpoint_rejects_raw_credential_material() -> None:
    with pytest.raises(ValueError, match="broker://"):
        OpenAICompatibleEndpoint(
            provider_id="remote",
            base_url="https://example.com/v1",
            credential_ref="raw-secret-value",
        )


def test_endpoint_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="embedded"):
        OpenAICompatibleEndpoint(
            provider_id="remote",
            base_url="https://user:secret@example.com/v1",
            credential_ref="broker://remote/api-key",
        )


def test_endpoint_rejects_query_and_fragment() -> None:
    with pytest.raises(ValueError, match="query or fragment"):
        OpenAICompatibleEndpoint(
            provider_id="remote",
            base_url="https://example.com/v1?token=x",
            credential_ref="broker://remote/api-key",
        )


def test_local_http_requires_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        OpenAICompatibleEndpoint(
            provider_id="local",
            base_url="http://127.0.0.1:8000/v1",
            credential_ref="broker://local/no-secret",
        )

    endpoint = OpenAICompatibleEndpoint(
        provider_id="local",
        base_url="http://127.0.0.1:8000/v1",
        credential_ref="broker://local/no-secret",
        allow_local_http=True,
    )
    assert endpoint.base_url.startswith("http://127.0.0.1")


def test_adapter_passes_only_credential_reference_to_transport() -> None:
    seen = {}

    def transport(endpoint: OpenAICompatibleEndpoint, model_id: str, prompt: str) -> str:
        seen["credential_ref"] = endpoint.credential_ref
        seen["model_id"] = model_id
        seen["prompt"] = prompt
        return "ok"

    endpoint = OpenAICompatibleEndpoint(
        provider_id="featherless",
        base_url="https://api.example.com/v1",
        credential_ref="broker://featherless/default",
    )
    adapter = OpenAICompatibleProviderAdapter(
        endpoint=endpoint,
        models=(_model("featherless"),),
        transport=transport,
    )

    assert adapter.invoke("model-a", "hello") == "ok"
    assert seen == {
        "credential_ref": "broker://featherless/default",
        "model_id": "model-a",
        "prompt": "hello",
    }


def test_adapter_rejects_unknown_model() -> None:
    endpoint = OpenAICompatibleEndpoint(
        provider_id="provider",
        base_url="https://example.com/v1",
        credential_ref="broker://provider/default",
    )
    adapter = OpenAICompatibleProviderAdapter(
        endpoint=endpoint,
        models=(_model("provider"),),
        transport=lambda *_: "ok",
    )
    with pytest.raises(ValueError, match="not registered"):
        adapter.invoke("unknown", "hello")


def test_model_identity_must_match_endpoint() -> None:
    endpoint = OpenAICompatibleEndpoint(
        provider_id="provider-a",
        base_url="https://example.com/v1",
        credential_ref="broker://provider-a/default",
    )
    with pytest.raises(ValueError, match="provider_id"):
        OpenAICompatibleProviderAdapter(
            endpoint=endpoint,
            models=(_model("provider-b"),),
            transport=lambda *_: "ok",
        )
