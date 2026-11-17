#!/usr/bin/env python3
"""Seed one low-risk proactive task when the CK-NEXUS queue is idle."""

from __future__ import annotations

import json
import os
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.proactive import ProactiveTaskSeeder
from creator_app.sqlite_security import configured_sqlite_database_id


def _task_database_path(configured_path: str | Path) -> Path:
    database_id = configured_sqlite_database_id(configured_path)
    if database_id == "control_plane_user_state":
        return Path("/root/.local/state/cknexus/control-plane.sqlite3")
    if database_id == "control_plane_var_lib":
        return Path("/var/lib/cknexus/control-plane/tasks.db")
    raise ValueError("configured path is not a task database")


def main() -> int:
    database = Path(
        os.getenv("CKNEXUS_TASK_DATABASE", "/root/.local/state/cknexus/control-plane.sqlite3")
    )
    try:
        database = _task_database_path(database)
        result = ProactiveTaskSeeder(TaskStore(database)).run_once()
        print(
            json.dumps(
                {
                    "ok": True,
                    "state": result.state,
                    "reason": result.reason,
                    "job_id": result.job_id,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        print(json.dumps({"ok": False, "error": "proactive_seed_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
