"""Seed one evidence-bounded proactive development task per UTC day."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from creator_app.control_plane.task_store import TaskStore


@dataclass(frozen=True, slots=True)
class ProactiveSeedResult:
    state: str
    reason: str
    job_id: str | None = None


class ProactiveTaskSeeder:
    def __init__(
        self,
        store: TaskStore,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.clock = clock

    def run_once(self) -> ProactiveSeedResult:
        now = self.clock().astimezone(UTC)
        job_id = f"n8n-proactive-{now:%Y-%m-%d}"
        if self.store.has_open_tasks():
            return ProactiveSeedResult("skipped", "queue_not_empty")
        payload = {
            "handler": "n8n_development_signal",
            "node_id": job_id,
            "task": "Evidence-backed proactive maintenance",
            "description": (
                "Inspect current repository code, tests, and sanitized prior outcomes. "
                "Choose exactly one small, measurable, low-risk improvement supported by "
                "repository evidence, within the allowlisted intelligence modules or Fast "
                "Control cache/probe modules. Add or update a focused regression test. "
                "Do not create generic TODOs, repeat a known failed approach, modify protected "
                "Auto Developer, Auto GitOps, learning-memory, task-queue, or policy-gate files, "
                "touch secrets, change dependencies, or run network, credential, release, or "
                "deployment commands. If no defensible improvement exists, make no change and "
                "explain why."
            ),
            "priority": 1,
            "source": "proactive_maintenance",
            "production_status": "NO-GO",
            "external_mutation_authorized": False,
            "release_evidence": False,
            "evidence_refs": ["policy://proactive-maintenance"],
        }
        try:
            self.store.enqueue(job_id, payload)
        except ValueError:
            return ProactiveSeedResult("skipped", "already_seeded_today", job_id)
        return ProactiveSeedResult("seeded", "daily_proactive_task_queued", job_id)
