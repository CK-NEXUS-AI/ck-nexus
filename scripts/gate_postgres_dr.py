#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
    with tempfile.TemporaryDirectory(prefix="cknexus-r19-dr-") as tmp:
        backup_dir = Path(tmp) / "backup"
        backup = subprocess.run(
            [
                sys.executable,
                "scripts/postgres_dr.py",
                "backup",
                "--source-url",
                source,
                "--output-dir",
                str(backup_dir),
            ],
            text=True,
            capture_output=True,
        )
        if backup.returncode != 0:
            result.update(
                status="BLOCKED" if backup.returncode == 2 else "FAIL", reason="backup_gate_failed"
            )
            print(json.dumps(result, sort_keys=True))
            return backup.returncode
        restore = subprocess.run(
            [
                sys.executable,
                "scripts/postgres_dr.py",
                "restore",
                "--source-url",
                source,
                "--target-url",
                target,
                "--backup-dir",
                str(backup_dir),
            ],
            text=True,
            capture_output=True,
        )
        result.update(
            status="PASS"
            if restore.returncode == 0
            else ("BLOCKED" if restore.returncode == 2 else "FAIL"),
            backup="completed",
            restore="completed" if restore.returncode == 0 else "not_passed",
        )
        print(json.dumps(result, sort_keys=True))
        return restore.returncode


if __name__ == "__main__":
    raise SystemExit(main())
