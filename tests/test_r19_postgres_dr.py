from __future__ import annotations

import hashlib
import io

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


def test_hash_stream_rewinds_and_returns_checksum_and_size():
    stream = io.BytesIO(b"safe fixture")
    digest, size = postgres_dr._hash_stream(stream)
    assert digest == hashlib.sha256(b"safe fixture").hexdigest()
    assert size == len(b"safe fixture")
    assert stream.tell() == 0


def test_database_connection_string_is_passed_through_environment_not_argv(monkeypatch):
    monkeypatch.setenv("PGHOST", "db.example")
    env = postgres_dr._database_environment("postgresql://user:secret@db.example/app")
    assert env["PGDATABASE"] == "app"
    assert env["PGHOST"] == "db.example"
    assert env["PGUSER"] == "user"
    assert env["PGPASSWORD"] == "secret"
