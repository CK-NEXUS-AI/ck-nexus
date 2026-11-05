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



def test_postgres_environment_uses_private_passfile_without_password_in_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CKNEXUS_DATABASE_URL", "postgresql://source:secret@db.example.test/source")
    monkeypatch.setenv("CKNEXUS_RESTORE_DATABASE_URL", "postgresql://target:secret@db.example.test/target_restore")
    env = postgres_dr._postgres_environment(
        "postgresql://operator:secret%3Avalue@db.example.test:5433/cknexus_restore?sslmode=require",
        tmp_path,
    )
    passfile = Path(env["PGPASSFILE"])
    assert passfile.is_file()
    assert passfile.stat().st_mode & 0o777 == 0o600
    assert r"secret\:value" in passfile.read_text(encoding="utf-8")
    assert "PGPASSWORD" not in env
    assert "CKNEXUS_DATABASE_URL" not in env
    assert "CKNEXUS_RESTORE_DATABASE_URL" not in env
    assert env["PGHOST"] == "db.example.test"
    assert env["PGPORT"] == "5433"
    assert env["PGDATABASE"] == "cknexus_restore"
    assert env["PGUSER"] == "operator"
    assert env["PGSSLMODE"] == "require"


def test_pgpass_escapes_delimiters():
    assert postgres_dr._pgpass_escape(r"user:name\value") == r"user\:name\\value"



def test_postgres_environment_rejects_control_characters(tmp_path):
    with pytest.raises(postgres_dr.DRBlocked, match="control characters"):
        postgres_dr._postgres_environment(
            "postgresql://operator:secret%0Ainjected@db.example.test/cknexus_restore",
            tmp_path,
        )


def test_restore_connects_pg_restore_to_isolated_target(tmp_path, monkeypatch):
    commands = []
    monkeypatch.setenv("CKNEXUS_ENVIRONMENT", "staging")
    monkeypatch.setenv("CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE", "YES")
    monkeypatch.setenv("CKNEXUS_RESTORE_TARGET_CLASS", "isolated-dr")
    monkeypatch.setattr(postgres_dr, "_require_tool", lambda name: name)
    monkeypatch.setattr(
        postgres_dr,
        "_postgres_environment",
        lambda url, credential_dir: {"PGDATABASE": "cknexus_restore_dr"},
    )
    monkeypatch.setattr(
        postgres_dr,
        "verify_dump",
        lambda backup_dir: {"status": "PASS", "sha256": "a" * 64},
    )

    def fake_run(command, *, env=None, stdin=None):
        commands.append(command)
        if command[0] == "pg_restore":
            return postgres_dr.subprocess.CompletedProcess(command, 0, "", "")
        return postgres_dr.subprocess.CompletedProcess(
            command,
            0,
            "\n".join(postgres_dr.REQUIRED_TABLES),
            "",
        )

    monkeypatch.setattr(postgres_dr, "_run", fake_run)
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "postgres.dump").write_bytes(b"fixture")
    (backup_dir / "SHA256SUMS").write_text("a" * 64 + "  postgres.dump\n")

    result = postgres_dr.restore(
        "postgresql://source:secret@db.example.test/cknexus",
        "postgresql://target:secret@db.example.test/cknexus_restore_dr",
        backup_dir,
        900,
    )

    assert result["status"] == "PASS"
    assert commands[0][:3] == ["pg_restore", "--dbname", "cknexus_restore_dr"]
    assert commands[1][0] == "psql"
