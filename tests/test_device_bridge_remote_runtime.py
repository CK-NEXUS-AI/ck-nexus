from __future__ import annotations

import pytest

from creator_app.device_bridge.remote_runtime import build_remote_server_from_environment


def _env(monkeypatch):
    values = {
        "CKNEXUS_REMOTE_RESOURCE_URL": "https://bridge.example.test/mcp",
        "CKNEXUS_REMOTE_ISSUER_URL": "https://auth.example.test",
        "CKNEXUS_REMOTE_JWKS_URL": "https://auth.example.test/.well-known/jwks.json",
        "CKNEXUS_REMOTE_ALLOWED_ALGORITHMS": "RS256",
        "CKNEXUS_REMOTE_SOURCE_COMMIT": "a" * 40,
        "CKNEXUS_REMOTE_SOURCE_TREE": "b" * 40,
        "CKNEXUS_REMOTE_REGISTRY_SHA256": "c" * 64,
        "CKNEXUS_REMOTE_DESCRIPTOR_SHA256": "d" * 64,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_runtime_fails_closed_when_provider_config_is_missing(monkeypatch):
    _env(monkeypatch)
    monkeypatch.delenv("CKNEXUS_REMOTE_ISSUER_URL", raising=False)
    with pytest.raises(ValueError, match="CKNEXUS_REMOTE_ISSUER_URL"):
        build_remote_server_from_environment()


def test_runtime_rejects_non_asymmetric_algorithm(monkeypatch):
    _env(monkeypatch)
    monkeypatch.setenv("CKNEXUS_REMOTE_ALLOWED_ALGORITHMS", "HS256")
    with pytest.raises(ValueError, match="allowed_algorithms"):
        build_remote_server_from_environment()


def test_runtime_builds_loopback_remote_server_from_explicit_config(monkeypatch):
    _env(monkeypatch)
    server = build_remote_server_from_environment()
    assert server.settings.host == "127.0.0.1"
    assert server.settings.stateless_http is True
    assert server.settings.auth is not None
    assert server.settings.auth.required_scopes == ["cknexus:read"]
    assert server.settings.auth.validate_token_resource is True
