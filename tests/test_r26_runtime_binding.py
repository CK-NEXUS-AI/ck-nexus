from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import creator_app.api as api_module
from creator_app.api import create_app
from creator_app.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "cknexus-test.db",
        mock_ai=True,
        access_token="",
        rate_limit_per_minute=20,
    )


def test_runtime_binding_disabled_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CKNEXUS_RUNTIME_BINDING_ENABLED", raising=False)
    verify = AsyncMock()
    monkeypatch.setattr(api_module, "verify_runtime_binding_or_raise", verify)
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/health/ready").status_code == 200
    verify.assert_not_awaited()


def test_runtime_binding_required_is_startup_gated_and_in_readiness(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_RUNTIME_BINDING_ENABLED", "true")
    verify = AsyncMock()
    close = AsyncMock()
    status = AsyncMock(return_value={"postgres": True, "redis": True})
    monkeypatch.setattr(api_module, "verify_runtime_binding_or_raise", verify)
    monkeypatch.setattr(api_module, "close_runtime_bindings", close)
    monkeypatch.setattr(api_module, "runtime_binding_status", status)

    with TestClient(create_app(_settings(tmp_path))) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        deps = {item["name"]: item for item in ready.json()["dependencies"]}
        assert deps["postgres-runtime-binding"]["state"] == "healthy"
        assert deps["redis-runtime-binding"]["state"] == "healthy"
    verify.assert_awaited_once()
    close.assert_awaited_once()


def test_runtime_binding_failure_blocks_readiness(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_RUNTIME_BINDING_ENABLED", "true")
    monkeypatch.setattr(api_module, "verify_runtime_binding_or_raise", AsyncMock())
    monkeypatch.setattr(api_module, "close_runtime_bindings", AsyncMock())
    monkeypatch.setattr(
        api_module,
        "runtime_binding_status",
        AsyncMock(return_value={"postgres": True, "redis": False}),
    )

    with TestClient(create_app(_settings(tmp_path))) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 503
        assert "REQUIRED_DEPENDENCY_UNAVAILABLE" in ready.json()["causes"]
