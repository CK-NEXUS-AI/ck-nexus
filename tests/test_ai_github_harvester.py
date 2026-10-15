from __future__ import annotations

import subprocess

from scripts import ai_github_harvester as harvester
from scripts.ai_github_harvester import classify_cli_error


def test_search_uses_get_for_repository_search(monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, '{"items": []}', "")

    monkeypatch.setattr(harvester.subprocess, "run", fake_run)

    assert harvester.search("topic:ai-agents stars:>100", limit=1) == []
    assert captured["command"][:4] == ["gh", "api", "-X", "GET"]
    assert "q=topic:ai-agents stars:>100" in captured["command"]


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
