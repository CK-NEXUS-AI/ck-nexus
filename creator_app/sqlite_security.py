"""Safe local SQLite path opening for private CK-NEXUS state databases.

The hardened backend requires POSIX geteuid and O_NOFOLLOW primitives. It fails
closed on platforms without them rather than silently weakening path checks.
"""

from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import suppress
from pathlib import Path
from typing import Any

_SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")
_DEFAULT_ISOLATION = object()


def prepare_private_sqlite_parent(path: str | Path) -> Path:
    """Create a private database directory; never chmod an existing directory."""
    if not hasattr(os, "geteuid") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("secure SQLite paths require POSIX geteuid and O_NOFOLLOW support")

    requested = Path(path).expanduser()
    # Existing paths may be shared with unrelated files. Do not change
    # their permissions; require an operator-created private DB directory.
    with suppress(FileExistsError):
        requested.parent.mkdir(parents=True, exist_ok=False, mode=0o700)

    parent = requested.parent.resolve(strict=True)
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    fd = os.open(parent, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISDIR(opened.st_mode):
            raise OSError("SQLite database parent must be a real directory")
        if opened.st_uid != os.geteuid():
            raise PermissionError("SQLite database directory must belong to the current user")
        if stat.S_IMODE(opened.st_mode) & 0o077:
            raise PermissionError(
                "SQLite database directory must already be private (mode 0700 or stricter); "
                "existing directory permissions are never changed automatically"
            )
        current = os.stat(parent, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError("SQLite database directory changed while preparing it")
        if stat.S_IMODE(current.st_mode) & 0o077:
            raise PermissionError("SQLite database directory is not private")
    finally:
        os.close(fd)
    return parent / requested.name


def _check_private_parent(path: Path) -> Path:
    if not hasattr(os, "geteuid") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("secure SQLite paths require POSIX geteuid and O_NOFOLLOW support")

    parent = path.parent.resolve(strict=True)
    uid = os.geteuid()
    for directory in (parent, *parent.parents):
        metadata = os.stat(directory, follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode):
            raise OSError("SQLite database parent chain must contain real directories")
        if metadata.st_uid not in (0, uid):
            raise PermissionError(
                "SQLite database parent chain must be owned by root or the current user"
            )
        mode = stat.S_IMODE(metadata.st_mode)
        if directory == parent and mode & 0o077:
            raise PermissionError(
                "SQLite database directory must be private (mode 0700 or stricter)"
            )
        if mode & 0o022 and not mode & stat.S_ISVTX:
            raise PermissionError(
                "SQLite database parent chain must not be group/world writable unless sticky"
            )
    return parent / path.name


def _open_checked(path: Path, *, writable: bool, create: bool) -> int:
    flags = (os.O_RDWR if writable else os.O_RDONLY) | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    if create:
        flags |= os.O_CREAT
    fd = os.open(path, flags, 0o600)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError("SQLite database and sidecars must be regular files")
        if opened.st_nlink != 1:
            raise OSError("SQLite database and sidecars must not be hard-linked")
        if opened.st_uid != os.geteuid():
            raise PermissionError("SQLite database and sidecars must belong to the current user")
        if writable:
            os.fchmod(fd, 0o600)
        elif stat.S_IMODE(opened.st_mode) & 0o077:
            raise PermissionError("read-only SQLite database and sidecars must have mode 0600")

        current = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != (
            opened.st_dev,
            opened.st_ino,
        ):
            raise OSError("SQLite path changed while opening")
        return fd
    except BaseException:
        os.close(fd)
        raise


def connect_sqlite_database(
    path: str | Path,
    *,
    timeout: float,
    readonly: bool = False,
    isolation_level: str | None | Any = _DEFAULT_ISOLATION,
) -> sqlite3.Connection:
    """Open SQLite only from a protected directory and regular private files.

    The database directory must already be private. Existing sidecars and
    sidecars visible during connection setup are checked. SQLite can create
    WAL/SHM sidecars later on first use; the private directory prevents other
    UIDs from replacing them. Processes running as the same UID share the
    documented local trust boundary.
    """
    requested = Path(path).expanduser()
    database = _check_private_parent(requested)

    checked_files: dict[Path, int] = {}
    connection: sqlite3.Connection | None = None
    try:
        checked_files[database] = _open_checked(
            database, writable=not readonly, create=not readonly
        )
        for suffix in _SIDECAR_SUFFIXES:
            sidecar = Path(f"{database}{suffix}")
            try:
                checked_files[sidecar] = _open_checked(sidecar, writable=not readonly, create=False)
            except FileNotFoundError:
                continue

        if readonly:
            uri = database.as_uri() + "?mode=ro"
            readonly_kwargs: dict[str, Any] = {"uri": True, "timeout": timeout}
            if isolation_level is not _DEFAULT_ISOLATION:
                readonly_kwargs["isolation_level"] = isolation_level
            connection = sqlite3.connect(uri, **readonly_kwargs)
        elif isolation_level is _DEFAULT_ISOLATION:
            connection = sqlite3.connect(database, timeout=timeout)
        else:
            connection = sqlite3.connect(database, timeout=timeout, isolation_level=isolation_level)

        # Validate sidecars visible during connection setup. SQLite may create
        # WAL/SHM later on first use; the private parent directory is the
        # cross-UID protection boundary for those later creations.
        for suffix in _SIDECAR_SUFFIXES:
            sidecar = Path(f"{database}{suffix}")
            if sidecar not in checked_files:
                try:
                    checked_files[sidecar] = _open_checked(
                        sidecar, writable=not readonly, create=False
                    )
                except FileNotFoundError:
                    continue

        for checked_path, fd in checked_files.items():
            try:
                current = os.stat(checked_path, follow_symlinks=False)
            except FileNotFoundError as exc:
                if checked_path == database:
                    raise OSError("SQLite database path disappeared while connecting") from exc
                # SQLite may legitimately remove a journal after recovery.
                continue
            opened = os.fstat(fd)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != (
                opened.st_dev,
                opened.st_ino,
            ):
                raise OSError("SQLite database or sidecar path changed while connecting")
        return connection
    except BaseException:
        if connection is not None:
            connection.close()
        raise
    finally:
        for fd in checked_files.values():
            os.close(fd)
