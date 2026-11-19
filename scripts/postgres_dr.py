#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

REQUIRED_TABLES = ("agnes_idempotency", "creator_runs", "email_journal", "email_outbox")


class DRBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class DbIdentity:
    host: str
    port: int | None
    database: str


def _identity(url: str) -> DbIdentity:
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise DRBlocked("database URL must use postgres:// or postgresql://")
    database = parsed.path.lstrip("/").split("?", 1)[0]
    if not parsed.hostname or not database:
        raise DRBlocked("database URL must include host and database name")
    return DbIdentity(parsed.hostname, parsed.port, database)


@contextmanager
def _libpq_connection(url: str) -> Iterator[dict[str, str]]:
    """Keep database passwords out of argv and disk using libpq PGPASSWORD."""
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query_passwords = [value for key, value in query if key.lower() == "password"]
    password = (
        unquote(parsed.password)
        if parsed.password is not None
        else (query_passwords[-1] if query_passwords else None)
    )
    username = unquote(parsed.username) if parsed.username is not None else None
    host = parsed.hostname or ""
    port = parsed.port or 5432
    database = unquote(parsed.path.lstrip("/"))
    env = os.environ.copy()
    # Do not let inherited libpq variables silently override the connection URL
    # (for example PGSSLMODE=disable or PGOPTIONS changing session behavior).
    for name in tuple(env):
        if name.startswith("PG") or name in {
            "CKNEXUS_DATABASE_URL",
            "CKNEXUS_RESTORE_DATABASE_URL",
        }:
            env.pop(name, None)
    env.update(PGHOST=host, PGPORT=str(port), PGDATABASE=database)
    if username is not None:
        env["PGUSER"] = username
    else:
        env.pop("PGUSER", None)
    if password is not None:
        # libpq reads PGPASSWORD from the child environment.
        env["PGPASSWORD"] = password
    libpq_env = {
        "sslmode": "PGSSLMODE",
        "sslrootcert": "PGSSLROOTCERT",
        "sslcert": "PGSSLCERT",
        "sslkey": "PGSSLKEY",
        "connect_timeout": "PGCONNECT_TIMEOUT",
        "application_name": "PGAPPNAME",
        "options": "PGOPTIONS",
        "target_session_attrs": "PGTARGETSESSIONATTRS",
        "gssencmode": "PGGSSENCMODE",
        "channel_binding": "PGCHANNELBINDING",
    }
    for key, value in query:
        env_name = libpq_env.get(key.lower())
        if env_name:
            env[env_name] = value
    yield env


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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def backup(source_url: str, output_dir: Path, rpo_seconds: int) -> dict[str, object]:
    pg_dump = _require_tool("pg_dump")
    _identity(source_url)
    output_dir.mkdir(parents=True, exist_ok=False)
    dump = output_dir / "postgres.dump"
    started = time.time()
    # output_dir is an operator-selected local path; the automated gate supplies
    # a fresh private temporary directory rather than request-controlled input.
    with _libpq_connection(source_url) as env, dump.open("wb") as fh:
        proc = subprocess.run(
            [pg_dump, "--format=custom", "--no-owner", "--no-acl"],
            env=env,
            stdout=fh,
            stderr=subprocess.PIPE,
            check=False,
        )
    if proc.returncode != 0:
        dump.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed with exit code {proc.returncode}")
    digest = _sha256(dump)
    finished = time.time()
    metadata = {
        "status": "PASS",
        "operation": "backup",
        "database": asdict(_identity(source_url)),
        "dump_file": dump.name,
        "sha256": digest,
        "size_bytes": dump.stat().st_size,
        "started_at_epoch": started,
        "finished_at_epoch": finished,
        "duration_seconds": round(finished - started, 3),
        "rpo_target_seconds": rpo_seconds,
    }
    (output_dir / "SHA256SUMS").write_text(f"{digest}  {dump.name}\n")
    (output_dir / "backup-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return metadata


def verify_dump(backup_dir: Path) -> dict[str, object]:
    dump = backup_dir / "postgres.dump"
    sums = backup_dir / "SHA256SUMS"
    if not dump.is_file() or not sums.is_file():
        raise DRBlocked("backup directory is missing postgres.dump or SHA256SUMS")
    expected = sums.read_text().split()[0]
    actual = _sha256(dump)
    if expected != actual:
        raise DRBlocked("backup checksum mismatch")
    return {"status": "PASS", "sha256": actual, "size_bytes": dump.stat().st_size}


def restore(
    source_url: str, target_url: str, backup_dir: Path, rto_seconds: int
) -> dict[str, object]:
    validate_restore_boundary(
        source_url,
        target_url,
        os.getenv("CKNEXUS_ENVIRONMENT", ""),
        os.getenv("CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE", ""),
        os.getenv("CKNEXUS_RESTORE_TARGET_CLASS", ""),
    )
    pg_restore = _require_tool("pg_restore")
    psql = _require_tool("psql")
    integrity = verify_dump(backup_dir)
    dump = backup_dir / "postgres.dump"
    started = time.time()
    with _libpq_connection(target_url) as env:
        proc = subprocess.run(
            [
                pg_restore,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                str(dump),
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = " ".join((proc.stderr or "").split())[:1200]
            raise RuntimeError(
                f"pg_restore failed with exit code {proc.returncode}: {detail}"
            )
        table_sql = (
            "SELECT tablename FROM pg_catalog.pg_tables "
            "WHERE schemaname='public' ORDER BY tablename;"
        )
        verify = subprocess.run(
            [psql, "-Atqc", table_sql],
            env=env,
            text=True,
            capture_output=True,
            check=False,
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
        "operation": "restore-drill",
        "target": asdict(_identity(target_url)),
        "backup_sha256": integrity["sha256"],
        "duration_seconds": round(duration, 3),
        "rto_target_seconds": rto_seconds,
        "required_tables_verified": list(REQUIRED_TABLES),
    }


if __name__ == "__main__":
    raise SystemExit("Use scripts/gate_postgres_dr.py; direct filesystem paths are not accepted.")
