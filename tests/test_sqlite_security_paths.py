from pathlib import Path

import pytest

from creator_app.sqlite_security import validate_configured_sqlite_path


def test_configured_sqlite_path_accepts_exact_service_database() -> None:
    assert validate_configured_sqlite_path(
        "/root/.local/state/cknexus/control-plane.sqlite3"
    ) == Path("/root/.local/state/cknexus/control-plane.sqlite3")


def test_configured_sqlite_path_rejects_unapproved_absolute_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        validate_configured_sqlite_path("/tmp/untrusted/tasks.db")


def test_configured_sqlite_path_rejects_traversal_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        validate_configured_sqlite_path(
            "/root/.local/state/cknexus/../outside/control-plane.sqlite3"
        )


def test_configured_sqlite_path_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        validate_configured_sqlite_path("control-plane.sqlite3")
