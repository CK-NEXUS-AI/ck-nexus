#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _database_environment(database_url: str) -> dict[str, str]:
    """Pass connection strings through libpq's environment, never command arguments."""
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


def backup(source_url: str, output_dir: Path, rpo_seconds: int) -> dict[str, object]:
    pg_dump = _require_tool("pg_dump")
    _identity(source_url)
    output_dir.mkdir(parents=True, exist_ok=False)
    dump = output_dir / "postgres.dump"
    started = time.time()
    with dump.open("wb") as fh:
        proc = subprocess.run(
            [pg_dump, "--format=custom", "--no-owner", "--no-acl"],
            env=_database_environment(source_url),
            stdout=fh,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
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
    target_env = _database_environment(target_url)
    proc = subprocess.run(
        [
            pg_restore,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            str(dump.resolve()),
        ],
        env=target_env,
        text=True,
        capture_output=True,
        check=False,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pg_restore failed with exit code {proc.returncode}")
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
    b.add_argument("--source-url", default=os.getenv("CKNEXUS_DATABASE_URL", ""))
    b.add_argument("--output-dir", required=True)
    b.add_argument(
        "--rpo-seconds", type=int, default=int(os.getenv("CKNEXUS_RPO_TARGET_SECONDS", "3600"))
    )
    r = sub.add_parser("restore")
    r.add_argument("--source-url", default=os.getenv("CKNEXUS_DATABASE_URL", ""))
    r.add_argument("--target-url", default=os.getenv("CKNEXUS_RESTORE_DATABASE_URL", ""))
    r.add_argument("--backup-dir", required=True)
    r.add_argument(
        "--rto-seconds", type=int, default=int(os.getenv("CKNEXUS_RTO_TARGET_SECONDS", "900"))
    )
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = backup(args.source_url, Path(args.output_dir), args.rpo_seconds)
        else:
            result = restore(
                args.source_url, args.target_url, Path(args.backup_dir), args.rto_seconds
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
