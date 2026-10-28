"""Seed one evidence-bounded proactive development task per UTC day."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from creator_app.control_plane.task_store import TaskStore

_ALLOWED_PROACTIVE_SOURCE_PATHS = (
    "creator_app/n8n_intelligence/analysis.py",
    "creator_app/n8n_intelligence/client.py",
    "creator_app/n8n_intelligence/collector.py",
    "creator_app/n8n_intelligence/models.py",
    "creator_app/n8n_intelligence/store.py",
    "creator_app/n8n_intelligence/task_bridge.py",
    "creator_app/control_plane/fast_cache.py",
    "creator_app/control_plane/fast_probe.py",
)


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
                "repository evidence. Approved source files (exact): "
                + ", ".join(f"`{path}`" for path in _ALLOWED_PROACTIVE_SOURCE_PATHS)
                + ". Add or update a focused regression test. "
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
        existing = self.store.get(job_id)
        if existing is not None:
            if existing.get("state") == "failed" and self.store.requeue_failed(
                job_id, max_attempts=3
            ):
                return ProactiveSeedResult("seeded", "retrying_failed_task", job_id)
            return ProactiveSeedResult("skipped", "already_seeded_today", job_id)
        try:
            self.store.enqueue(job_id, payload)
        except ValueError:
            return ProactiveSeedResult("skipped", "already_seeded_today", job_id)
        return ProactiveSeedResult("seeded", "daily_proactive_task_queued", job_id)
