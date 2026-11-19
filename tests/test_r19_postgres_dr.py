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


def test_libpq_connection_uses_environment_without_writing_password_to_disk(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CKNEXUS_DATABASE_URL", "postgresql://env-user:placeholder@db.example/source")
    monkeypatch.setenv("PGPASSFILE", "/tmp/old-passfile")
    url = "postgresql://ck-user:unit-test-value@db.example:5433/source_restore?sslmode=require"
    with postgres_dr._libpq_connection(url) as env:
        assert env["PGHOST"] == "db.example"
        assert env["PGPORT"] == "5433"
        assert env["PGDATABASE"] == "source_restore"
        assert env["PGUSER"] == "ck-user"
        assert env["PGPASSWORD"] == "unit-test-value"
        assert env["PGSSLMODE"] == "require"
        assert "CKNEXUS_DATABASE_URL" not in env
        assert "CKNEXUS_RESTORE_DATABASE_URL" not in env
        assert "PGPASSFILE" not in env


def test_libpq_connection_preserves_passwordless_url():
    url = "postgresql://reader@db.example:5432/catalog?sslmode=verify-full"
    with postgres_dr._libpq_connection(url) as env:
        assert env["PGHOST"] == "db.example"
        assert env["PGDATABASE"] == "catalog"
        assert "PGPASSWORD" not in env
        assert "PGPASSFILE" not in env


def test_postgres_dr_gate_uses_internal_temp_path_and_in_process_helpers(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    from scripts import gate_postgres_dr

    monkeypatch.setenv("CKNEXUS_DATABASE_URL", "postgresql://source:secret@db.example/source")
    monkeypatch.setenv(
        "CKNEXUS_RESTORE_DATABASE_URL",
        "postgresql://target:secret@db.example/source_restore",
    )
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "staging")
    monkeypatch.setenv("CKNEXUS_RESTORE_TARGET_CLASS", "isolated-dr")
    monkeypatch.setenv("CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE", "YES")
    monkeypatch.setattr(gate_postgres_dr.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls: dict[str, Path] = {}

    def fake_backup(source_url: str, output_dir: Path, rpo_seconds: int) -> dict[str, object]:
        assert source_url.startswith("postgresql://source:")
        assert output_dir.name == "backup"
        assert "cknexus-r19-dr-" in str(output_dir.parent)
        output_dir.mkdir()
        calls["backup"] = output_dir
        return {"status": "PASS", "sha256": "a" * 64}

    def fake_restore(
        source_url: str, target_url: str, backup_dir: Path, rto_seconds: int
    ) -> dict[str, object]:
        assert backup_dir == calls["backup"]
        assert backup_dir.is_dir()
        return {"status": "PASS", "duration_seconds": 1.25}

    monkeypatch.setattr(gate_postgres_dr.postgres_dr, "backup", fake_backup)
    monkeypatch.setattr(gate_postgres_dr.postgres_dr, "restore", fake_restore)

    assert gate_postgres_dr.main() == 0
    output = __import__("json").loads(capsys.readouterr().out)
    assert output["status"] == "PASS"
    assert output["backup_sha256"] == "a" * 64
