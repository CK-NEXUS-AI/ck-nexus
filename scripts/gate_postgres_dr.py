#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from scripts import postgres_dr


def main() -> int:
    source = os.getenv("CKNEXUS_DATABASE_URL", "").strip()
    target = os.getenv("CKNEXUS_RESTORE_DATABASE_URL", "").strip()
    result = {
        "gate": "R19_POSTGRES_DR",
        "source_configured": bool(source),
        "target_configured": bool(target),
        "pg_dump_available": bool(shutil.which("pg_dump")),
        "pg_restore_available": bool(shutil.which("pg_restore")),
        "psql_available": bool(shutil.which("psql")),
    }
    if not source or not target:
        result.update(status="BLOCKED", reason="source_or_isolated_restore_url_not_configured")
        print(json.dumps(result, sort_keys=True))
        return 2
    missing = [x for x in ("pg_dump", "pg_restore", "psql") if not shutil.which(x)]
    if missing:
        result.update(
            status="BLOCKED", reason="postgres_client_tools_unavailable:" + ",".join(missing)
        )
        print(json.dumps(result, sort_keys=True))
        return 2
    if (
        os.getenv("CKNEXUS_ENVIRONMENT") != "staging"
        or os.getenv("CKNEXUS_RESTORE_TARGET_CLASS") != "isolated-dr"
        or os.getenv("CKNEXUS_ALLOW_DESTRUCTIVE_RESTORE") != "YES"
    ):
        result.update(
            status="BLOCKED", reason="explicit_isolated_staging_restore_approval_not_configured"
        )
        print(json.dumps(result, sort_keys=True))
        return 2

    # The backup path is created internally in a private temporary directory.
    # No command-line or request-supplied filesystem path reaches the DR helpers.
    with tempfile.TemporaryDirectory(prefix="cknexus-r19-dr-") as tmp:
        backup_dir = Path(tmp) / "backup"
        try:
            backup = postgres_dr.backup(
                source,
                backup_dir,
                int(os.getenv("CKNEXUS_RPO_TARGET_SECONDS", "3600")),
            )
            restore = postgres_dr.restore(
                source,
                target,
                backup_dir,
                int(os.getenv("CKNEXUS_RTO_TARGET_SECONDS", "900")),
            )
        except postgres_dr.DRBlocked as exc:
            result.update(status="BLOCKED", reason=str(exc))
            print(json.dumps(result, sort_keys=True))
            return 2
        except Exception as exc:
            result.update(status="FAIL", reason=f"{type(exc).__name__}:{exc}")
            print(json.dumps(result, sort_keys=True))
            return 1

    passed = backup.get("status") == "PASS" and restore.get("status") == "PASS"
    result.update(
        status="PASS" if passed else "FAIL",
        backup="completed",
        backup_sha256=backup.get("sha256"),
        restore="completed" if restore.get("status") == "PASS" else "not_passed",
        restore_duration_seconds=restore.get("duration_seconds"),
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
