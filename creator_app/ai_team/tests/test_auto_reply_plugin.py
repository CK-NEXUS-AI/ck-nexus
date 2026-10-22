from __future__ import annotations

import io
import json
import urllib.error

import pytest

from creator_app.ai_team.auto_reply_plugin import (
    AutoReplyError,
    AutoReplyPlugin,
    _approved_base_url,
)


class FakePool:
    def __init__(self, selections):
        self.selections = list(selections)
        self.failures = []
        self.successes = []

    def acquire(self):
        return self.selections.pop(0) if self.selections else None

    def report_failure(self, key_id, *, status_code=None):
        self.failures.append((key_id, status_code))

    def report_success(self, key_id):
        self.successes.append(key_id)

    def get_status_summary(self):
        return {
            "keys": [
                {
                    "id": "model-studio-1",
                    "provider": "model-studio-1",
                    "model": "qwen-test",
                    "healthy": True,
                    "exhausted": False,
                    "consecutive_failures": 0,
                    "source": "environment",
                    "api_key": "MUST_NOT_APPEAR",
                }
            ]
        }


class Selection:
    def __init__(
        self,
        key_id="key-1",
        provider="qwen",
        model="qwen-test",
        api_key="secret-do-not-print",
        base_url="https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    ):
        self.key_id = key_id
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_fast_reply_uses_configured_provider_and_redacts_secrets():
    pool = FakePool([Selection()])
    requests = []

    def open_url(request, *, timeout):
        requests.append((request, timeout))
        return FakeResponse({"choices": [{"message": {"content": "สวัสดีครับ"}}]})

    plugin = AutoReplyPlugin(pool_factory=lambda: pool, open_url=open_url)
    result = plugin.reply("ตอบเร็ว", max_tokens=64)

    assert result["ok"] is True
    assert result["provider"] == "qwen"
    assert result["response"] == "สวัสดีครับ"
    assert result["attempts"] == 1
    assert requests[0][1] <= 8
    assert b"secret-do-not-print" not in requests[0][0].data
    assert pool.successes == ["key-1"]


def test_provider_http_error_falls_back_to_next_key_without_leaking_body():
    first = Selection(key_id="bad-key", provider="first")
    second = Selection(key_id="good-key", provider="second")
    pool = FakePool([first, second])
    calls = []

    def open_url(request, *, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                request.full_url, 429, "limited", {}, io.BytesIO(b"private error payload")
            )
        return FakeResponse({"choices": [{"message": {"content": "fallback answer"}}]})

    plugin = AutoReplyPlugin(pool_factory=lambda: pool, open_url=open_url, max_attempts=2)
    result = plugin.reply("fallback test")

    assert result["response"] == "fallback answer"
    assert result["fallback_used"] is True
    assert result["attempts"] == 2
    assert pool.failures == [("bad-key", 429)]
    assert pool.successes == ["good-key"]


def test_unapproved_endpoint_is_rejected_without_network_request():
    pool = FakePool([Selection(base_url="http://127.0.0.1:11434/v1")])
    calls = []

    def open_url(*args, **kwargs):
        calls.append(True)
        raise AssertionError("network must not be called")

    plugin = AutoReplyPlugin(pool_factory=lambda: pool, open_url=open_url)
    with pytest.raises(AutoReplyError) as error:
        plugin.reply("should be blocked")
    assert error.value.code == "PROVIDERS_UNAVAILABLE"

    assert calls == []
    assert pool.failures == [("key-1", 403)]


def test_empty_prompt_and_excessive_token_limit_are_rejected():
    plugin = AutoReplyPlugin(pool_factory=lambda: None)
    with pytest.raises(AutoReplyError) as empty_error:
        plugin.reply(" ")
    assert empty_error.value.code == "EMPTY_PROMPT"
    with pytest.raises(AutoReplyError) as token_error:
        plugin.reply("hello", max_tokens=99999)
    assert token_error.value.code == "INVALID_TOKEN_LIMIT"


def test_status_does_not_expose_credential_fields():
    plugin = AutoReplyPlugin(pool_factory=lambda: FakePool([Selection()]))
    status = plugin.status()

    assert status["secret_values_exposed"] is False
    assert status["providers"][0]["health_status"] == "healthy"
    assert "api_key" not in json.dumps(status).lower()
    assert "MUST_NOT_APPEAR" not in json.dumps(status)


def test_status_does_not_misreport_unprobed_provider_as_unhealthy():
    class UnprobedPool(FakePool):
        def get_status_summary(self):
            return {
                "keys": [
                    {
                        "id": "model-studio-1",
                        "provider": "model-studio-1",
                        "model": "qwen-test",
                        "healthy": False,
                        "exhausted": False,
                        "consecutive_failures": 0,
                        "source": "environment",
                    }
                ]
            }

    status = AutoReplyPlugin(pool_factory=lambda: UnprobedPool([])).status()
    provider = status["providers"][0]
    assert provider["healthy"] is None
    assert provider["health_status"] == "unknown"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://api.openai.com/v1", True),
        ("https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1", True),
        ("http://api.openai.com/v1", False),
        ("https://api.openai.com.attacker.example/v1", False),
        ("https://user:pass@api.openai.com/v1", False),
        ("http://127.0.0.1:11434/v1", False),
    ],
)
def test_provider_endpoint_allowlist(url, expected):
    assert _approved_base_url(url) is expected
