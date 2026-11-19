#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

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
def _libpq_connection(url: str) -> Iterator[tuple[str, dict[str, str]]]:
    """Keep database passwords out of argv by using a private temporary pgpass file."""
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query_passwords = [value for key, value in query if key.lower() == "password"]
    password = (
        unquote(parsed.password)
        if parsed.password is not None
        else (query_passwords[-1] if query_passwords else None)
    )
    safe_query = urlencode([(key, value) for key, value in query if key.lower() != "password"])
    username = unquote(parsed.username) if parsed.username is not None else None
    host = parsed.hostname or "*"
    port = parsed.port or 5432
    database = unquote(parsed.path.lstrip("/")) or "*"
    host_literal = f"[{host}]" if ":" in host else host
    authority = f"{quote(username, safe='')}@" if username is not None else ""
    authority += host_literal
    if parsed.port is not None:
        authority += f":{parsed.port}"
    safe_url = urlunsplit((parsed.scheme, authority, parsed.path, safe_query, parsed.fragment))
    env = os.environ.copy()
    env.pop("CKNEXUS_DATABASE_URL", None)
    env.pop("CKNEXUS_RESTORE_DATABASE_URL", None)
    if password is None:
        yield safe_url, env
        return

    def escape_pgpass(value: str) -> str:
        return value.replace("\\", "\\\\").replace(":", "\\:")

    with tempfile.TemporaryDirectory(prefix="cknexus-pgpass-") as directory:
        passfile = Path(directory) / "pgpass"
        fields = (host, str(port), database, username or "*", password)
        passfile.write_text(
            ":".join(escape_pgpass(value) for value in fields) + "\n", encoding="utf-8"
        )
        passfile.chmod(0o600)
        env["PGPASSFILE"] = str(passfile)
        yield safe_url, env


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
    with _libpq_connection(source_url) as (safe_source_url, env), dump.open("wb") as fh:
        proc = subprocess.run(
            [pg_dump, "--dbname", safe_source_url, "--format=custom", "--no-owner", "--no-acl"],
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
    with _libpq_connection(target_url) as (safe_target_url, env):
        proc = subprocess.run(
            [
                pg_restore,
                "--dbname",
                safe_target_url,
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
            raise RuntimeError(f"pg_restore failed with exit code {proc.returncode}")
        table_sql = (
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename;"
        )
        verify = subprocess.run(
            [psql, safe_target_url, "-Atqc", table_sql],
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CK-NEXUS PostgreSQL backup/isolated restore drill"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--output-dir", required=True)
    b.add_argument(
        "--rpo-seconds", type=int, default=int(os.getenv("CKNEXUS_RPO_TARGET_SECONDS", "3600"))
    )
    r = sub.add_parser("restore")
    r.add_argument("--backup-dir", required=True)
    r.add_argument(
        "--rto-seconds", type=int, default=int(os.getenv("CKNEXUS_RTO_TARGET_SECONDS", "900"))
    )
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = backup(
                os.getenv("CKNEXUS_DATABASE_URL", ""), Path(args.output_dir), args.rpo_seconds
            )
        else:
            result = restore(
                os.getenv("CKNEXUS_DATABASE_URL", ""),
                os.getenv("CKNEXUS_RESTORE_DATABASE_URL", ""),
                Path(args.backup_dir),
                args.rto_seconds,
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
