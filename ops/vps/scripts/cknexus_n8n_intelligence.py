#!/usr/bin/env python3
"""Run one bounded n8n intelligence collection cycle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.circuit_breaker import PersistentCircuitBreaker
from creator_app.n8n_intelligence.client import N8NReadClient
from creator_app.n8n_intelligence.collector import CollectorConfig, N8NIntelligenceCollector
from creator_app.n8n_intelligence.store import N8NIntelligenceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CK-NEXUS n8n Development Intelligence")
    parser.add_argument(
        "--base-url", default=os.getenv("N8N_INTEL_BASE_URL", "http://127.0.0.1:5678/api/v1")
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        default=Path(os.getenv("N8N_INTEL_KEY_FILE", "/root/.config/n8n/api_key")),
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(
            os.getenv("N8N_INTEL_DATABASE", "/var/lib/cknexus/n8n-intelligence/events.db")
        ),
    )
    parser.add_argument(
        "--task-database",
        type=Path,
        default=Path(os.getenv("CKNEXUS_TASK_DATABASE", "/var/lib/cknexus/control-plane/tasks.db")),
    )
    parser.add_argument(
        "--slow-seconds", type=float, default=float(os.getenv("N8N_INTEL_SLOW_SECONDS", "30"))
    )
    parser.add_argument(
        "--max-executions", type=int, default=int(os.getenv("N8N_INTEL_MAX_EXECUTIONS", "50"))
    )
    return parser


def run(
    client, database: Path, task_database: Path, slow_seconds: float, max_executions: int
) -> int:
    intelligence = N8NIntelligenceStore(database)
    task_store = TaskStore(task_database)
    collector = N8NIntelligenceCollector(
        client, intelligence, task_store, CollectorConfig(slow_seconds, max_executions)
    )
    report = collector.run_once()
    print(
        json.dumps(
            {
                "ok": report.error is None,
                "fetched": report.fetched,
                "accepted": report.accepted,
                "ignored": report.ignored,
                "new_events": report.new_events,
                "duplicate_events": report.duplicate_events,
                "tasks_created": report.tasks_created,
                "error": report.error,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report.error is None else 1


def main() -> int:
    args = build_parser().parse_args()
    try:
        circuit_path = Path(
            os.getenv(
                "N8N_INTEL_CIRCUIT_STATE",
                "/var/lib/cknexus/n8n-intelligence/circuit-breaker.json",
            )
        )
        client = N8NReadClient(
            args.base_url,
            args.key_file,
            max_items=args.max_executions,
            circuit_breaker=PersistentCircuitBreaker(circuit_path),
        )
        return run(
            client, args.database, args.task_database, args.slow_seconds, args.max_executions
        )
    except Exception:
        print(json.dumps({"ok": False, "error": "collector_initialization_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
