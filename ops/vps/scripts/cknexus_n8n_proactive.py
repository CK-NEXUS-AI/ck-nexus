#!/usr/bin/env python3
"""Seed one low-risk proactive task when the CK-NEXUS queue is idle."""

from __future__ import annotations

import json
import os
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.proactive import ProactiveTaskSeeder


def main() -> int:
    database = Path(
        os.getenv("CKNEXUS_TASK_DATABASE", "/root/.local/state/cknexus/control-plane.sqlite3")
    )
    try:
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
