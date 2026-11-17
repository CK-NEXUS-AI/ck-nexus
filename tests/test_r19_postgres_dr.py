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


def test_database_connection_string_is_passed_through_environment_not_argv(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.example")
    env = postgres_dr._database_environment("postgresql://user:secret@db.example/app")
    assert env["PGDATABASE"] == "app"
    assert env["PGHOST"] == "db.example"
    assert env["PGUSER"] == "user"
    assert env["PGPASSWORD"] == "secret"


def test_backup_directory_rejects_paths_outside_private_temp_storage(tmp_path: Path):
    with pytest.raises(postgres_dr.DRBlocked, match="approved temporary storage"):
        postgres_dr._validated_backup_dir(Path("/etc"))


def test_backup_directory_rejects_group_or_world_accessible_directory(tmp_path: Path):
    tmp_path.chmod(0o755)
    with pytest.raises(postgres_dr.DRBlocked, match="private directory"):
        postgres_dr._validated_backup_dir(tmp_path)


def test_backup_directory_creation_requires_private_parent(tmp_path: Path):
    tmp_path.chmod(0o755)
    with pytest.raises(postgres_dr.DRBlocked, match="parent directory must be private"):
        postgres_dr._validated_backup_dir(tmp_path / "backup", create=True)
