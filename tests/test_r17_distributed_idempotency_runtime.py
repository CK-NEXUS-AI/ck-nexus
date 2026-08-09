from __future__ import annotations

import sys
from pathlib import Path

import pytest

from creator_app.agnes_runtime import AgnesNervousSystem
from creator_app.config import Settings

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "creator_app" / "skills" / "agnes" / "SKILL.md"


def _make(tmp_path: Path, **kwargs):
    return AgnesNervousSystem(
        skill_file=SKILLS,
        ledger_path=tmp_path / "ledger.jsonl",
        sandbox_enabled=True,
        sandbox_root=tmp_path / "sandbox",
        sandbox_repository_root=ROOT,
        phase3_enabled=True,
        **kwargs,
    )


def test_phase3_production_fails_closed_without_distributed_url(tmp_path: Path):
    with pytest.raises(RuntimeError, match="CKNEXUS_AGNES_REDIS_URL"):
        _make(tmp_path, environment="production")


def test_phase3_staging_rejects_non_redis_scheme(tmp_path: Path):
    with pytest.raises(RuntimeError, match="unsupported Redis URL scheme"):
        _make(tmp_path, environment="staging", phase3_redis_url="http://redis.invalid")


def test_phase3_development_keeps_local_durable_store(tmp_path: Path):
    agnes = _make(tmp_path, environment="development")
    status = agnes.status()["execution_kernel"]["idempotency"]
    assert status["backend"] == "SQLiteIdempotencyStore"
    assert status["durable"] is True
    assert status["distributed"] is False
    assert status["production_safe"] is False


def test_settings_reads_agnes_redis_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("CKNEXUS_HOME", str(tmp_path))
    monkeypatch.setenv("CKNEXUS_AGNES_REDIS_URL", "rediss://redis.example.invalid:6380/0")
    settings = Settings.from_env()
    assert settings.agnes_redis_url == "rediss://redis.example.invalid:6380/0"


def test_phase3_production_reports_missing_redis_client_without_secret_leak(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "redis", None)
    monkeypatch.delitem(sys.modules, "redis.asyncio", raising=False)
    secret_url = "rediss://user:super-secret@example.invalid:6380/0"
    with pytest.raises(RuntimeError) as exc:
        _make(tmp_path, environment="production", phase3_redis_url=secret_url)
    assert "redis client is unavailable" in str(exc.value)
    assert "super-secret" not in str(exc.value)


def test_postgres_idempotency_migration_exists_with_primary_key():
    migration = (ROOT / "migrations" / "postgresql" / "003_agnes_idempotency.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS agnes_idempotency" in migration
    assert "idem_key TEXT PRIMARY KEY" in migration
    assert "result_json JSONB" in migration


def test_production_compose_requires_redis_health_and_wires_agnes_url():
    compose = (ROOT / "docker-compose.prod.yml").read_text()
    assert "redis:\n        condition: service_healthy" in compose
    assert "CKNEXUS_AGNES_REDIS_URL: redis://redis:6379/0" in compose
    assert 'test: ["CMD", "redis-cli", "ping"]' in compose
