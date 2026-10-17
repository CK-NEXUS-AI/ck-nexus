from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from creator_app.unified_control import _migrate_legacy_development_status_db


def _create_database(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as database:
        database.execute("CREATE TABLE state (value TEXT NOT NULL)")
        database.execute("INSERT INTO state(value) VALUES (?)", (value,))


def _read_value(path: Path) -> str:
    with sqlite3.connect(path) as database:
        row = database.execute("SELECT value FROM state").fetchone()
    assert row is not None
    return str(row[0])


def test_migrates_legacy_state_to_persistent_path(tmp_path: Path):
    legacy = (
        tmp_path / "home" / ".local" / "state" / "ck-nexus" / "development-status.sqlite3"
    )
    target = tmp_path / "data" / "development-status.sqlite3"
    _create_database(legacy, "preserve-me")

    _migrate_legacy_development_status_db(target, legacy)

    assert target.is_file()
    assert _read_value(target) == "preserve-me"
    # The source remains intact for rollback and forensic comparison.
    assert _read_value(legacy) == "preserve-me"


def test_migration_never_overwrites_existing_target(tmp_path: Path):
    legacy = tmp_path / "legacy.sqlite3"
    target = tmp_path / "data" / "development-status.sqlite3"
    _create_database(legacy, "legacy")
    _create_database(target, "current")

    _migrate_legacy_development_status_db(target, legacy)

    assert _read_value(target) == "current"


def test_migration_is_noop_when_legacy_state_is_absent(tmp_path: Path):
    legacy = tmp_path / "missing.sqlite3"
    target = tmp_path / "data" / "development-status.sqlite3"

    _migrate_legacy_development_status_db(target, legacy)

    assert not target.exists()


def test_migration_closes_source_if_destination_open_fails(tmp_path: Path, monkeypatch):
    import creator_app.unified_control as unified_control

    legacy = tmp_path / "legacy.sqlite3"
    target = tmp_path / "data" / "development-status.sqlite3"
    _create_database(legacy, "preserve-me")
    original_connect = unified_control.sqlite3.connect
    source_connections = []

    def connect(path, *args, **kwargs):
        if Path(path) == legacy:
            connection = original_connect(path, *args, **kwargs)
            source_connections.append(connection)
            return connection
        if Path(path) != legacy:
            raise sqlite3.OperationalError("simulated destination open failure")
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(unified_control.sqlite3, "connect", connect)
    try:
        _migrate_legacy_development_status_db(target, legacy)
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError("expected destination open failure")

    assert len(source_connections) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        source_connections[0].execute("SELECT 1")
