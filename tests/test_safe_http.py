from __future__ import annotations

import pytest

from scripts._safe_http import _check_loopback, loopback_api_base_url


def test_loopback_api_url_uses_fixed_host_and_validated_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CKNEXUS_API_PORT", "8123")
    assert loopback_api_base_url() == "http://127.0.0.1:8123"


def test_loopback_api_url_rejects_host_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CKNEXUS_API_PORT", "example.com:80")
    with pytest.raises(ValueError):
        loopback_api_base_url()


def test_loopback_api_url_rejects_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CKNEXUS_API_PORT", "65536")
    with pytest.raises(ValueError):
        loopback_api_base_url()


def test_loopback_http_accepts_only_loopback_targets() -> None:
    _check_loopback("http://127.0.0.1:8000/health")
    _check_loopback("http://[::1]:8000/health")
    with pytest.raises(ValueError):
        _check_loopback("http://169.254.169.254/latest/meta-data")
    with pytest.raises(ValueError):
        _check_loopback("https://attacker.example/collect")
    with pytest.raises(ValueError):
        _check_loopback("http://user:pass@127.0.0.1:8000/health")
