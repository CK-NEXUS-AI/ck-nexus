from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.global_knowledge import searxng_runtime


ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        content_type: str = "application/json",
        body: bytes = b'{"results": []}',
    ) -> None:
        self.status = status
        self._content_type = content_type
        self._body = body

    def read(self) -> bytes:
        return self._body

    def getheader(self, name: str, default: str = "") -> str:
        if name.lower() == "content-type":
            return self._content_type
        return default


class FakeConnection:
    response = FakeResponse()
    calls: list[tuple[str, str, dict[str, str]]] = []

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
    ) -> None:
        self.calls.append((method, path, headers))

    def getresponse(self) -> FakeResponse:
        return self.response

    def close(self) -> None:
        return None


def install_fake_connection(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse,
) -> None:
    FakeConnection.response = response
    FakeConnection.calls = []
    monkeypatch.setattr(
        searxng_runtime.http.client,
        "HTTPConnection",
        FakeConnection,
    )


def test_validate_local_base_url_accepts_loopback_only() -> None:
    assert searxng_runtime.validate_local_base_url(
        "http://127.0.0.1:8080/"
    ) == ("127.0.0.1", 8080)

    with pytest.raises(ValueError, match="loopback"):
        searxng_runtime.validate_local_base_url("http://192.168.1.10:8080/")

    with pytest.raises(ValueError, match="local http"):
        searxng_runtime.validate_local_base_url("https://127.0.0.1:8080/")


def test_json_doctor_accepts_expected_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        FakeResponse(body=b'{"results": [{"url": "https://example.test"}]}'),
    )

    result = searxng_runtime.check_json_api(
        "http://127.0.0.1:8080/",
        query="ck nexus",
    )

    assert result.ok is True
    assert result.reason == "ready"
    assert result.result_count == 1
    assert "format=json" in FakeConnection.calls[0][1]
    assert FakeConnection.calls[0][2]["X-Real-IP"] == "127.0.0.1"


def test_json_doctor_fails_closed_when_json_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        FakeResponse(
            content_type="text/html",
            body=b"<html></html>",
        ),
    )

    result = searxng_runtime.check_json_api("http://127.0.0.1:8080/")

    assert result.ok is False
    assert result.reason == "json_format_not_enabled"


def test_json_doctor_fails_closed_on_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_connection(
        monkeypatch,
        FakeResponse(body=b'{"unexpected": []}'),
    )

    result = searxng_runtime.check_json_api("http://127.0.0.1:8080/")

    assert result.ok is False
    assert result.reason == "results_array_missing"


def test_runtime_settings_enable_json_limiter_and_valkey() -> None:
    settings = (ROOT / "deploy/searxng/settings.yml").read_text()

    assert "    - json" in settings
    assert "  limiter: true" in settings
    assert "valkey://valkey:6379/0" in settings


def test_compose_binds_search_to_loopback_and_does_not_publish_valkey() -> None:
    compose = (ROOT / "deploy/searxng/docker-compose.yml").read_text()

    assert '127.0.0.1:${SEARXNG_PORT:-8080}:8080' in compose

    valkey_block, searxng_block = compose.split("  searxng:", maxsplit=1)
    assert "ports:" not in valkey_block
    assert "SEARXNG_SECRET:" in searxng_block
    assert "./limiter.toml:/etc/searxng/limiter.toml:ro" in searxng_block


def test_limiter_passlist_is_restricted_to_loopback() -> None:
    limiter = (ROOT / "deploy/searxng/limiter.toml").read_text()

    assert '"127.0.0.0/8"' in limiter
    assert '"::1"' in limiter
    assert "192.168.0.0/16" not in limiter
    assert "0.0.0.0/0" not in limiter


def test_example_environment_contains_no_committed_secret() -> None:
    env_text = (ROOT / "deploy/searxng/.env.example").read_text()
    values: dict[str, str] = {}

    for raw_line in env_text.splitlines():
        if not raw_line or raw_line.startswith("#"):
            continue
        key, value = raw_line.split("=", maxsplit=1)
        values[key] = value

    assert values["SEARXNG_SECRET"] == ""
