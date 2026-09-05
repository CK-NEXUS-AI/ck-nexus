#!/usr/bin/env python3
"""Print CK-NEXUS collaborative development live status."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from creator_app.development_control import DevelopmentStatusStore


def _store() -> DevelopmentStatusStore:
    path = os.environ.get(
        "CKNEXUS_DEVELOPMENT_STATUS_DB",
        "~/.local/state/ck-nexus/development-status.sqlite3",
    )
    return DevelopmentStatusStore(Path(path))


def _value(value: object) -> str:
    return "UNKNOWN" if value is None else str(value)


def print_text(snapshot: dict[str, object]) -> None:
    counts = snapshot["task_counts"]
    competency = snapshot["competency"]
    release = snapshot["release_authority"]
    scores = snapshot["scores"]

    print(
        "CK-NEXUS LIVE STATUS — "
        f"UPDATE: {snapshot['observed_at']} / freshness <= "
        f"{snapshot['freshness_target_seconds']}s"
    )
    print("=" * 72)
    print("COMPLETED")
    for task in snapshot["completed"]:
        print(
            f"- {task['task_id']} {task['title']} "
            f"commit={_value(task['commit_hash'])}"
        )
    print("ACTIVE")
    for task in snapshot["active"]:
        print(
            f"- {task['task_id']} {task['title']} state={task['state']} "
            f"progress={_value(task['progress'])} "
            f"step={_value(task['current_step'])} eta={_value(task['eta'])}"
        )
    print("QUEUED")
    for task in snapshot["queued"]:
        print(
            f"- {task['task_id']} {task['title']} "
            f"priority={task['priority']} state={task['state']}"
        )
    print("BLOCKED")
    for task in snapshot["blocked"]:
        print(
            f"- {task['task_id']} {task['title']} "
            f"reason={_value(task['blocker'])}"
        )
    print("SCORES / GATES")
    print(
        f"- OpenSSF: {_value(scores['openssf_scorecard_current'])} "
        f"target={scores['openssf_scorecard_target']}"
    )
    print(
        f"- Q10={release['q10']} Q11={release['q11']} "
        f"Q12={release['q12']}"
    )
    print(f"- Production={release['production']}")
    print("AI COMPETENCY")
    print(
        f"- total={competency['total']} "
        f"pro_write={competency['pro_level_write_enabled']} "
        f"observer_or_pending={competency['observer_or_pending']} "
        f"not_eligible={competency['not_eligible']}"
    )
    next_task = snapshot["next_task"]
    print("=" * 72)
    if next_task is None:
        print("NEXT: NONE")
    else:
        print(
            f"NEXT: {next_task['task_id']} {next_task['title']} "
            f"{next_task['state']} {next_task['priority']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--history", type=int, default=0)
    args = parser.parse_args()
    store = _store()

    if args.history:
        print(json.dumps(store.history(args.history), indent=2, sort_keys=True))
        return 0

    snapshot = store.snapshot()
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print_text(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
