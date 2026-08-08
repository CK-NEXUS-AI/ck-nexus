from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.config import Settings, _as_bool, _as_int


def test_boolean_parser():
    assert _as_bool("true") is True
    assert _as_bool("ON") is True
    assert _as_bool("0") is False
    assert _as_bool(None, default=True) is True


def test_integer_parser_uses_bounds_and_safe_default():
    assert _as_int("12", default=5, minimum=1, maximum=20) == 12
    assert _as_int("999", default=5, minimum=1, maximum=20) == 20
    assert _as_int("invalid", default=5, minimum=1, maximum=20) == 5


def test_runtime_home_controls_relative_database_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_DATABASE_PATH", "state/creator.db")
    configured = Settings.from_env()
    assert configured.database_path == tmp_path / "state" / "creator.db"


def test_production_startup_fails_closed_without_access_token(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "production")
    monkeypatch.delenv("CKNEXUS_ACCESS_TOKEN", raising=False)

    try:
        Settings.from_env()
    except RuntimeError as exc:
        assert "CKNEXUS_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("production must not start without access authentication")


def test_production_email_gateway_requires_webhook_secret(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "production")
    monkeypatch.setenv("CKNEXUS_ACCESS_TOKEN", "runtime-access-secret")
    monkeypatch.setenv("CKNEXUS_EMAIL_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN", "CHANGE_ME_RANDOM")

    try:
        Settings.from_env()
    except RuntimeError as exc:
        assert "CKNEXUS_EMAIL_WEBHOOK_TOKEN" in str(exc)
    else:
        raise AssertionError("production email gateway must require a real webhook secret")


def test_nonproduction_keeps_local_fail_open_compatibility(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "development")
    monkeypatch.delenv("CKNEXUS_ACCESS_TOKEN", raising=False)

    configured = Settings.from_env()

    assert configured.environment == "development"
    assert configured.access_token == ""


def test_production_oauth_requires_encrypted_vault(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "production")
    monkeypatch.setenv("CKNEXUS_ACCESS_TOKEN", "runtime-access-secret")
    monkeypatch.setenv("CKNEXUS_GMAIL_OAUTH_ENABLED", "true")
    monkeypatch.delenv("CKNEXUS_VAULT_ENABLED", raising=False)
    monkeypatch.delenv("CKNEXUS_VAULT_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        Settings.from_env()

    message = str(exc_info.value)
    assert "CKNEXUS_VAULT_ENABLED" in message
    assert "CKNEXUS_VAULT_KEY" in message
