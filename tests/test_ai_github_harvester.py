from __future__ import annotations

from scripts.ai_github_harvester import classify_cli_error


def test_classify_rate_limit_without_echoing_cli_output() -> None:
    assert classify_cli_error("HTTP 429: API rate limit exceeded") == "rate_limited"


def test_classify_authentication_error() -> None:
    assert classify_cli_error("HTTP 401: Bad credentials") == "authentication_failed"


def test_classify_permission_error() -> None:
    assert classify_cli_error("Resource not accessible by integration") == "permission_denied"


def test_unknown_error_is_safe_and_generic() -> None:
    secret_like_text = "fatal: token=ghp_example_private_value"
    category = classify_cli_error(secret_like_text)
    assert category == "unclassified_cli_error"
    assert "ghp_example_private_value" not in category
