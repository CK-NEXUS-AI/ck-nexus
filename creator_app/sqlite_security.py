"""Safe local SQLite path opening for private CK-NEXUS state databases."""

from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path
from typing import Any

_SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")
_DEFAULT_ISOLATION = object()


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

    Parent-directory ownership and permissions prevent other UIDs from
    replacing checked paths between descriptor validation and SQLite opening.
    Processes running as the same UID are inside the same local trust boundary.
    Existing and newly-created journal/WAL/SHM sidecars are checked as well.
    """
    requested = Path(path)
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
            connection = sqlite3.connect(uri, uri=True, timeout=timeout)
        elif isolation_level is _DEFAULT_ISOLATION:
            connection = sqlite3.connect(database, timeout=timeout)
        else:
            connection = sqlite3.connect(database, timeout=timeout, isolation_level=isolation_level)

        # SQLite may create WAL/SHM files while opening a WAL-mode database.
        # Validate those newly-created sidecars before returning the connection.
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
            except FileNotFoundError:
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
