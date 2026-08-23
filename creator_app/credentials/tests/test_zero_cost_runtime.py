from __future__ import annotations

import json

import pytest

from creator_app.credentials.zero_cost_runtime import (
    LocalOllamaRuntime,
    ZeroCostRuntimeUnavailable,
)


class FakeResponse:
    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class FakeConnection:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, str, bytes | None, dict[str, str] | None]] = []
        self.closed = False

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.requests.append((method, url, body, headers))

    def getresponse(self) -> FakeResponse:
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.connections: list[FakeConnection] = []
        self.calls: list[tuple[str, int, float]] = []

    def __call__(self, host: str, port: int, timeout: float) -> FakeConnection:
        self.calls.append((host, port, timeout))
        connection = FakeConnection([self.responses.pop(0)])
        self.connections.append(connection)
        return connection


def _local_model(name: str = "qwen3:8b") -> dict:
    return {
        "name": name,
        "model": name,
        "size": 4_000_000_000,
        "digest": "abc123",
        "details": {"format": "gguf"},
    }


def _runtime(
    factory: FakeFactory,
    *,
    enabled: bool = True,
    base_url: str = "http://127.0.0.1:11434",
    model: str = "qwen3:8b",
) -> LocalOllamaRuntime:
    return LocalOllamaRuntime(
        enabled=enabled,
        base_url=base_url,
        model=model,
        timeout=5,
        connection_factory=factory,
    )


def test_disabled_runtime_does_not_touch_network() -> None:
    factory = FakeFactory([])
    status = _runtime(factory, enabled=False).status()

    assert status.ready is False
    assert status.reason == "disabled"
    assert factory.calls == []


def test_non_loopback_url_is_rejected_before_network() -> None:
    factory = FakeFactory([])
    status = _runtime(factory, base_url="http://192.168.1.10:11434").status()

    assert status.ready is False
    assert "loopback-only" in status.reason
    assert factory.calls == []


def test_localhost_is_pinned_to_loopback_ip() -> None:
    factory = FakeFactory([FakeResponse(200, {"models": [_local_model()]})])
    status = _runtime(factory, base_url="http://localhost:11434").status()

    assert status.ready is True
    assert factory.calls[0][0] == "127.0.0.1"


def test_installed_local_model_is_ready() -> None:
    factory = FakeFactory([FakeResponse(200, {"models": [_local_model()]})])
    status = _runtime(factory).status()

    assert status.ready is True
    assert status.local_only is True
    assert status.reason == "verified local Ollama model"
    assert factory.connections[0].requests[0][0:2] == ("GET", "/api/tags")


def test_missing_model_fails_closed() -> None:
    factory = FakeFactory([FakeResponse(200, {"models": [_local_model("other:1b")]})])
    status = _runtime(factory).status()

    assert status.ready is False
    assert "not installed locally" in status.reason


@pytest.mark.parametrize("model", ["gpt-oss:120b-cloud", "example:cloud"])
def test_cloud_style_model_name_is_rejected_without_network(model: str) -> None:
    factory = FakeFactory([])
    status = _runtime(factory, model=model).status()

    assert status.ready is False
    assert "cloud model" in status.reason
    assert factory.calls == []


def test_remote_model_metadata_is_rejected() -> None:
    remote = _local_model()
    remote["remote_model"] = "provider/model"
    remote["remote_host"] = "https://ollama.com"
    factory = FakeFactory([FakeResponse(200, {"models": [remote]})])

    status = _runtime(factory).status()

    assert status.ready is False
    assert "remote/cloud" in status.reason


def test_incomplete_local_metadata_is_rejected() -> None:
    model = _local_model()
    model["size"] = 0
    factory = FakeFactory([FakeResponse(200, {"models": [model]})])

    status = _runtime(factory).status()

    assert status.ready is False
    assert "metadata is incomplete" in status.reason


def test_chat_executes_only_after_local_verification() -> None:
    factory = FakeFactory(
        [
            FakeResponse(200, {"models": [_local_model()]}),
            FakeResponse(200, {"message": {"content": "local answer"}}),
        ]
    )
    runtime = _runtime(factory)

    answer = runtime.chat("hello")

    assert answer == "local answer"
    method, path, body, headers = factory.connections[1].requests[0]
    assert (method, path) == ("POST", "/api/chat")
    assert headers == {"Content-Type": "application/json"}
    assert body is not None
    payload = json.loads(body.decode("utf-8"))
    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False


def test_chat_fails_closed_if_runtime_cannot_be_verified() -> None:
    factory = FakeFactory([FakeResponse(200, {"models": []})])
    runtime = _runtime(factory)

    with pytest.raises(ZeroCostRuntimeUnavailable, match="not installed locally"):
        runtime.chat("hello")

    assert len(factory.connections) == 1


def test_environment_invalid_timeout_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_OLLAMA_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("CKNEXUS_OLLAMA_TIMEOUT_SECONDS", "not-a-number")

    runtime = LocalOllamaRuntime.from_environment()

    assert runtime.timeout == LocalOllamaRuntime.default_timeout
