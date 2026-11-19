from __future__ import annotations

from scripts import ai_github_harvester as harvester
from scripts.ai_github_harvester import classify_cli_error


def test_search_uses_fixed_github_api_origin_and_encoded_query(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def read(self, _limit):
            return b'{"items": []}'

    class FakeConnection:
        def __init__(self, host, timeout):
            captured["host"] = host
            captured["timeout"] = timeout

        def request(self, method, path, headers):
            captured["method"] = method
            captured["path"] = path
            captured["authorization"] = headers["Authorization"]

        def getresponse(self):
            return Response()

        def close(self):
            captured["closed"] = True

    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setattr(harvester.http.client, "HTTPSConnection", FakeConnection)

    assert harvester.search("topic:ai-agents stars:>100", limit=1) == []
    assert captured["host"] == "api.github.com"
    assert captured["method"] == "GET"
    assert "q=topic%3Aai-agents+stars%3A%3E100" in captured["path"]
    assert captured["authorization"] == "Bearer test-token"
    assert captured["timeout"] == 20
    assert captured["closed"] is True


def test_classify_rate_limit_without_echoing_cli_output() -> None:
    assert classify_cli_error("HTTP 429: API rate limit exceeded") == "rate_limited"


def test_classify_authentication_error() -> None:
    assert classify_cli_error("HTTP 401: Bad credentials") == "authentication_failed"


def test_classify_permission_error() -> None:
    assert classify_cli_error("Resource not accessible by integration") == "permission_denied"


def test_classify_invalid_query_error() -> None:
    assert classify_cli_error("HTTP 422: Validation Failed") == "invalid_query"


def test_unknown_error_is_safe_and_generic() -> None:
    secret_like_text = "fatal: token=ghp_example_private_value"
    category = classify_cli_error(secret_like_text)
    assert category == "unclassified_cli_error"
    assert "ghp_example_private_value" not in category


def test_search_rejects_shell_metacharacters_before_subprocess(monkeypatch) -> None:
    monkeypatch.setattr(
        harvester.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )
    import pytest

    for query in ("topic:mcp; touch /tmp/pwned", "$(id)", "topic:mcp\n--help", "`id`"):
        with pytest.raises(ValueError):
            harvester.search(query)
