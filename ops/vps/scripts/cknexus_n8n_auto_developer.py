#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.auto_developer import AutoDeveloper


def build_parser():
    p = argparse.ArgumentParser(description="CK-NEXUS n8n Auto Developer")
    p.add_argument("--repo", type=Path, default=Path(os.getenv("CKNEXUS_REPO", "/root/ck-nexus")))
    p.add_argument(
        "--task-database",
        type=Path,
        default=Path(os.getenv("CKNEXUS_TASK_DATABASE", "/var/lib/cknexus/control-plane/tasks.db")),
    )
    p.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path(
            os.getenv("CKNEXUS_AUTO_DEV_EVIDENCE", "/var/lib/cknexus/n8n-intelligence/auto-dev")
        ),
    )
    p.add_argument("--timeout", type=int, default=int(os.getenv("CKNEXUS_AUTO_DEV_TIMEOUT", "180")))
    p.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(
            os.getenv("CKNEXUS_AUTO_DEV_WORKSPACES", "/var/lib/cknexus/n8n-intelligence/worktrees")
        ),
    )
    return p


def run(repo, task_database, evidence_dir, timeout, workspace_root=None):
    result = AutoDeveloper(
        TaskStore(task_database),
        repo=repo,
        evidence_dir=evidence_dir,
        timeout_seconds=timeout,
        workspace_root=workspace_root,
    ).run_once()
    print(
        json.dumps(
            {
                "ok": result.state in {"idle", "verified", "blocked"},
                "state": result.state,
                "reason": result.reason,
                "exit_code": result.exit_code,
                "tests_ok": result.tests_ok,
                "changed_paths": list(result.changed_paths),
                "evidence_path": result.evidence_path,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result.state in {"idle", "verified", "blocked"} else 1


def main():
    a = build_parser().parse_args()
    try:
        return run(a.repo, a.task_database, a.evidence_dir, a.timeout, a.workspace_root)
    except Exception:
        print(json.dumps({"ok": False, "error": "auto_developer_initialization_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
