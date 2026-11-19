from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import postgres_dr


def test_restore_boundary_rejects_non_staging():
    with pytest.raises(postgres_dr.DRBlocked, match="staging"):
        postgres_dr.validate_restore_boundary(
            "postgresql://u:p@db/source",
            "postgresql://u:p@db/source_restore",
            "production",
            "YES",
            "isolated-dr",
        )


def test_restore_boundary_requires_explicit_approval():
    with pytest.raises(postgres_dr.DRBlocked, match="ALLOW_DESTRUCTIVE"):
        postgres_dr.validate_restore_boundary(
            "postgresql://u:p@db/source",
            "postgresql://u:p@db/source_restore",
            "staging",
            "NO",
            "isolated-dr",
        )


def test_restore_boundary_rejects_same_database():
    with pytest.raises(postgres_dr.DRBlocked, match="same database"):
        postgres_dr.validate_restore_boundary(
            "postgresql://u:a@db/prod", "postgresql://u:b@db/prod", "staging", "YES", "isolated-dr"
        )


def test_restore_boundary_requires_dr_named_database():
    with pytest.raises(postgres_dr.DRBlocked, match="visibly identify"):
        postgres_dr.validate_restore_boundary(
            "postgresql://u:p@db/prod", "postgresql://u:p@db/test", "staging", "YES", "isolated-dr"
        )


def test_restore_boundary_accepts_isolated_target():
    source, target = postgres_dr.validate_restore_boundary(
        "postgresql://u:p@db/prod",
        "postgresql://u:p@db/prod_restore",
        "staging",
        "YES",
        "isolated-dr",
    )
    assert source.database == "prod"
    assert target.database == "prod_restore"


def test_verify_dump_checksum(tmp_path: Path):
    dump = tmp_path / "postgres.dump"
    dump.write_bytes(b"safe fixture")
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    (tmp_path / "SHA256SUMS").write_text(f"{digest}  postgres.dump\n")
    result = postgres_dr.verify_dump(tmp_path)
    assert result["status"] == "PASS"
    assert result["sha256"] == digest


def test_verify_dump_rejects_checksum_mismatch(tmp_path: Path):
    (tmp_path / "postgres.dump").write_bytes(b"changed")
    (tmp_path / "SHA256SUMS").write_text("0" * 64 + "  postgres.dump\n")
    with pytest.raises(postgres_dr.DRBlocked, match="checksum"):
        postgres_dr.verify_dump(tmp_path)


def test_libpq_connection_removes_password_from_url_and_uses_private_pgpass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("CKNEXUS_DATABASE_URL", "postgresql://env-user:env-secret@db.example/source")
    url = "postgresql://ck-user:p%3Ass%5Cword@db.example:5433/source_restore?sslmode=require"
    with postgres_dr._libpq_connection(url) as (safe_url, env):
        assert "p%3Ass" not in safe_url
        assert "@db.example" in safe_url and "p%3A" not in safe_url
        assert safe_url == "postgresql://ck-user@db.example:5433/source_restore?sslmode=require"
        assert "CKNEXUS_DATABASE_URL" not in env
        passfile = Path(env["PGPASSFILE"])
        assert passfile.exists()
        assert passfile.stat().st_mode & 0o777 == 0o600
        assert passfile.read_text(encoding="utf-8") == (
            "db.example:5433:source_restore:ck-user:p\\:ss\\\\word\n"
        )
    assert not passfile.exists()


def test_libpq_connection_preserves_passwordless_url():
    url = "postgresql://reader@db.example:5432/catalog?sslmode=verify-full"
    with postgres_dr._libpq_connection(url) as (safe_url, env):
        assert safe_url == url
        assert "PGPASSFILE" not in env
