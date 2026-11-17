import pytest

from creator_app.sqlite_security import configured_sqlite_database_id


def test_configured_sqlite_path_accepts_exact_service_database() -> None:
    assert (
        configured_sqlite_database_id("/root/.local/state/cknexus/control-plane.sqlite3")
        == "control_plane_user_state"
    )


def test_configured_sqlite_path_rejects_unapproved_absolute_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        configured_sqlite_database_id("/tmp/untrusted/tasks.db")


def test_configured_sqlite_path_rejects_traversal_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        configured_sqlite_database_id("/root/.local/state/cknexus/../outside/control-plane.sqlite3")


def test_configured_sqlite_path_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match="not an approved CK-NEXUS database path"):
        configured_sqlite_database_id("control-plane.sqlite3")
