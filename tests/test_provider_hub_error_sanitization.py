from __future__ import annotations

import logging

from creator_app import provider_hub


def _raise_sensitive_error(*args, **kwargs):
    raise RuntimeError("Traceback: /srv/private/config/provider-secret.json")


def test_generic_provider_errors_are_sanitized_and_logged_safely(monkeypatch, caplog) -> None:
    monkeypatch.setattr(provider_hub, "_require_known_validation_url", lambda _url: None)
    monkeypatch.setattr(provider_hub, "urlopen", _raise_sensitive_error)

    with caplog.at_level(logging.WARNING, logger=provider_hub.__name__):
        result = provider_hub._validate_generic("test-key", "https://api.groq.com/openai/v1/models")

    assert result == {"valid": False, "error": "Provider validation failed"}
    assert "private" not in str(result)
    assert "RuntimeError" in caplog.text
    assert "provider-secret.json" not in caplog.text


def test_anthropic_provider_errors_are_sanitized_and_logged_safely(monkeypatch, caplog) -> None:
    monkeypatch.setattr(provider_hub, "urlopen", _raise_sensitive_error)

    with caplog.at_level(logging.WARNING, logger=provider_hub.__name__):
        result = provider_hub._validate_anthropic("test-key")

    assert result == {"valid": False, "error": "Provider validation failed"}
    assert "private" not in str(result)
    assert "RuntimeError" in caplog.text
    assert "provider-secret.json" not in caplog.text
