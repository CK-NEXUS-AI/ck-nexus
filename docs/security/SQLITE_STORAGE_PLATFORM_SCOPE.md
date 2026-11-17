# CK-NEXUS SQLite storage security scope

## Supported security backend

The hardened SQLite path backend currently requires POSIX os.geteuid and
os.O_NOFOLLOW support. It is intended for Linux and macOS deployments.

On platforms without these primitives (including native Windows Python), the
backend fails closed with OSError. It does not silently fall back to ordinary
SQLite path opening. This restriction applies to the hardened Brain Journal
and Ebook Knowledge Store paths; it does not claim that every other CK-NEXUS
component is unavailable on Windows.

A Windows-native implementation needs handle-based reparse-point checks,
stable file identity checks, and private ACL verification before it can be
supported. A simple is_symlink() check is not an equivalent security boundary
and is not used as a fallback.

## Existing directory migration

The SQLite helper creates a missing database parent with mode 0700. If the
parent already exists, it never changes that directory's permissions because
the directory may contain unrelated files. It requires the directory to
already be owned by the service user and private (mode 0700 or stricter).
Otherwise initialization fails closed with PermissionError.

For an existing POSIX installation:

1. Stop the CK-NEXUS service that owns the database.
2. Identify the exact database directory and confirm it is dedicated to that
   database. Do not change permissions on a shared directory such as a common
   .state folder.
3. Prefer moving the database and its SQLite sidecars into a dedicated
   service-owned directory with mode 0700, preserving the files and owner.
4. If the existing directory is already dedicated, an operator may set its
   owner and mode explicitly (for example, install -d -m 700 -o SERVICE_USER
   -g SERVICE_GROUP /path/to/dedicated-db-dir). Do not apply chmod to a
   generic parent directory.
5. Restart the service and verify the database and sidecar files are owned by
   the service identity and have mode 0600.

No automatic migration or permission change is performed by the application.
