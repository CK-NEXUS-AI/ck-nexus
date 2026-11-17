from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.sqlite_security import validate_configured_sqlite_path


def test_configured_sqlite_path_accepts_database_under_trusted_root(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    root.mkdir()
    requested = root / "state.sqlite3"

    assert validate_configured_sqlite_path(requested, allowed_roots=(root,)) == requested


def test_configured_sqlite_path_rejects_path_outside_trusted_roots(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted"
    untrusted = tmp_path / "untrusted"
    trusted.mkdir()
    untrusted.mkdir()

    with pytest.raises(ValueError, match="outside approved storage roots"):
        validate_configured_sqlite_path(untrusted / "state.sqlite3", allowed_roots=(trusted,))


def test_configured_sqlite_path_rejects_traversal_outside_trusted_root(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()

    with pytest.raises(ValueError, match="traversal segments"):
        validate_configured_sqlite_path(
            trusted / ".." / "untrusted" / "state.sqlite3",
            allowed_roots=(trusted,),
        )


def test_configured_sqlite_path_rejects_non_database_suffix(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()

    with pytest.raises(ValueError, match="database file extension"):
        validate_configured_sqlite_path(trusted / "credentials.json", allowed_roots=(trusted,))


def test_configured_sqlite_path_rejects_symlink_escape(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted"
    untrusted = tmp_path / "untrusted"
    trusted.mkdir()
    untrusted.mkdir()
    outside = untrusted / "state.sqlite3"
    outside.touch()
    link = trusted / "state.sqlite3"
    link.symlink_to(outside)

    with pytest.raises(ValueError, match="outside approved storage roots"):
        validate_configured_sqlite_path(link, allowed_roots=(trusted,))
