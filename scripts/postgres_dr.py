#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, unquote, urlsplit

REQUIRED_TABLES = ("agnes_idempotency", "creator_runs", "email_journal", "email_outbox")


class DRBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class DbIdentity:
    host: str
    port: int | None
    database: str


def _identity(url: str) -> DbIdentity:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise DRBlocked("database URL contains an invalid port") from exc
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise DRBlocked("database URL must use postgres:// or postgresql://")
    database = parsed.path.lstrip("/").split("?", 1)[0]
    if not parsed.hostname or not database:
        raise DRBlocked("database URL must include host and database name")
    return DbIdentity(parsed.hostname, port, database)


def _same_database(a: DbIdentity, b: DbIdentity) -> bool:
    return (a.host.lower(), a.port or 5432, a.database.lower()) == (
        b.host.lower(),
        b.port or 5432,
        b.database.lower(),
    )


def validate_restore_boundary(
    source_url: str, target_url: str, environment: str, allow: str, target_class: str
) -> tuple[DbIdentity, DbIdentity]:
    if environment != "staging":
        raise DRBlocked("restore drill requires CKNEXUS_ENVIRONMENT=staging")
    if allow != "YES":
        raise DRBlocked("restore drill requires CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE=YES")
    if target_class != "isolated-dr":
        raise DRBlocked("restore target must declare CKNEXUS_RESTORE_TARGET_CLASS=isolated-dr")
    source = _identity(source_url)
    target = _identity(target_url)
    if _same_database(source, target):
        raise DRBlocked("source and restore target resolve to the same database identity")
    target_name = target.database.lower()
    if not any(token in target_name for token in ("restore", "drill", "_dr", "-dr")):
        raise DRBlocked("restore target database name must visibly identify a DR/restore database")
    return source, target


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise DRBlocked(f"required PostgreSQL client tool unavailable:{name}")
    return path


def _database_environment(database_url: str) -> dict[str, str]:
    """Pass connection fields through libpq's environment, never process arguments."""
    _identity(database_url)
    parsed = urlsplit(database_url)
    env = os.environ.copy()
    env["PGHOST"] = parsed.hostname or ""
    env["PGDATABASE"] = parsed.path.lstrip("/").split("?", 1)[0]
    if parsed.port is not None:
        env["PGPORT"] = str(parsed.port)
    if parsed.username is not None:
        env["PGUSER"] = unquote(parsed.username)
    if parsed.password is not None:
        env["PGPASSWORD"] = unquote(parsed.password)
    query = parse_qs(parsed.query, strict_parsing=False)
    allowed_options = {
        "sslmode": "PGSSLMODE",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "application_name": "PGAPPNAME",
        "target_session_attrs": "PGTARGETSESSIONATTRS",
    }
    for key, env_name in allowed_options.items():
        values = query.get(key)
        if values and len(values) == 1:
            env[env_name] = values[0]
    return env


def _hash_stream(stream) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    stream.seek(0)
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
        size += len(block)
    stream.seek(0)
    return digest.hexdigest(), size


def drill(
    source_url: str, target_url: str, rpo_seconds: int, rto_seconds: int
) -> dict[str, object]:
    """Back up and restore through an anonymous temporary file; accept no file paths."""
    source, target = validate_restore_boundary(
        source_url,
        target_url,
        os.getenv("CKNEXUS_ENVIRONMENT", ""),
        os.getenv("CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE", ""),
        os.getenv("CKNEXUS_RESTORE_TARGET_CLASS", ""),
    )
    pg_dump = _require_tool("pg_dump")
    pg_restore = _require_tool("pg_restore")
    psql = _require_tool("psql")
    source_env = _database_environment(source_url)
    target_env = _database_environment(target_url)
    started = time.time()

    with tempfile.TemporaryFile(mode="w+b") as dump_stream:
        backup = subprocess.run(
            [pg_dump, "--format=custom", "--no-owner", "--no-acl"],
            env=source_env,
            stdout=dump_stream,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            close_fds=True,
        )
        if backup.returncode != 0:
            raise RuntimeError(f"pg_dump failed with exit code {backup.returncode}")
        digest, size = _hash_stream(dump_stream)
        if size == 0:
            raise RuntimeError("pg_dump produced an empty backup")

        restore = subprocess.run(
            [pg_restore, "--clean", "--if-exists", "--no-owner", "--no-acl"],
            env=target_env,
            stdin=dump_stream,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            close_fds=True,
        )
        if restore.returncode != 0:
            raise RuntimeError(f"pg_restore failed with exit code {restore.returncode}")

    table_sql = (
        "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename;"
    )
    verify = subprocess.run(
        [psql, "-Atqc", table_sql],
        env=target_env,
        text=True,
        capture_output=True,
        check=False,
        shell=False,
        close_fds=True,
    )
    if verify.returncode != 0:
        raise RuntimeError(
            f"post-restore verification query failed with exit code {verify.returncode}"
        )
    tables = {line.strip() for line in verify.stdout.splitlines() if line.strip()}
    missing = sorted(set(REQUIRED_TABLES) - tables)
    if missing:
        raise RuntimeError("post-restore required tables missing:" + ",".join(missing))

    finished = time.time()
    duration = finished - started
    return {
        "status": "PASS" if duration <= rto_seconds else "FAIL",
        "operation": "postgres-backup-and-restore-drill",
        "source": asdict(source),
        "target": asdict(target),
        "backup_sha256": digest,
        "backup_size_bytes": size,
        "duration_seconds": round(duration, 3),
        "rpo_target_seconds": rpo_seconds,
        "rto_target_seconds": rto_seconds,
        "required_tables_verified": list(REQUIRED_TABLES),
    }


def main() -> int:
    source = os.getenv("CKNEXUS_DATABASE_URL", "").strip()
    target = os.getenv("CKNEXUS_RESTORE_DATABASE_URL", "").strip()
    try:
        if not source or not target:
            raise DRBlocked("source_or_isolated_restore_url_not_configured")
        result = drill(
            source,
            target,
            int(os.getenv("CKNEXUS_RPO_TARGET_SECONDS", "3600")),
            int(os.getenv("CKNEXUS_RTO_TARGET_SECONDS", "900")),
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1
    except DRBlocked as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:
        print(
            json.dumps({"status": "FAIL", "reason": f"{type(exc).__name__}:{exc}"}, sort_keys=True)
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
