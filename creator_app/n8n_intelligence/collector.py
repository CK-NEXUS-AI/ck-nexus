"""Orchestrate bounded n8n collection into the CK-NEXUS task queue."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creator_app.control_plane.task_store import TaskStore

from .analysis import classify_execution, fingerprint_execution, sanitize_message
from .client import N8NReadError
from .models import N8NExecutionEvent
from .store import N8NIntelligenceStore
from .task_bridge import build_task


@dataclass(frozen=True, slots=True)
class CollectorConfig:
    slow_seconds: float = 30.0
    max_executions: int = 50

    @classmethod
    def from_env(cls) -> CollectorConfig:
        slow = float(os.getenv("N8N_INTEL_SLOW_SECONDS", "30"))
        limit = int(os.getenv("N8N_INTEL_MAX_EXECUTIONS", "50"))
        if slow <= 0 or not 1 <= limit <= 50:
            raise ValueError("invalid n8n intelligence configuration")
        return cls(slow, limit)


@dataclass(frozen=True, slots=True)
class CollectorReport:
    fetched: int
    accepted: int
    ignored: int
    new_events: int
    duplicate_events: int
    tasks_created: int
    job_ids: tuple[str, ...] = ()
    error: str | None = None


class N8NIntelligenceCollector:
    def __init__(
        self,
        client: Any,
        intelligence: N8NIntelligenceStore,
        task_store: TaskStore,
        config: CollectorConfig,
    ) -> None:
        self.client = client
        self.intelligence = intelligence
        self.task_store = task_store
        self.config = config

    def run_once(self) -> CollectorReport:
        checkpoint = self.intelligence.checkpoint()
        try:
            rows, _ = self.client.list_executions()
        except N8NReadError as exc:
            # Publish only a bounded category, never the raw upstream message.
            message = str(exc).lower()
            if (
                "http error 401" in message
                or "http error 403" in message
                or ("circuit open" in message and "authentication" in message)
            ):
                reason = "authentication_failure"
            elif "circuit open" in message:
                reason = "circuit_open"
            else:
                reason = "upstream_failure"
            return CollectorReport(0, 0, 0, 0, 0, 0, error=reason)
        except Exception:
            return CollectorReport(0, 0, 0, 0, 0, 0, error="upstream_failure")

        fetched = len(rows)
        accepted = ignored = new_events = duplicate_events = tasks_created = 0
        job_ids: list[str] = []
        newest_id: str | None = None
        for row in rows[: self.config.max_executions]:
            execution_id = str(row.get("id") or "")
            if not execution_id:
                ignored += 1
                continue
            if newest_id is None:
                newest_id = execution_id
            if checkpoint and execution_id == checkpoint:
                break
            accepted += 1
            signal = classify_execution(row, self.config.slow_seconds)
            if signal is None:
                event = self._event(row, "info", "success", "")
            else:
                event = self._event(
                    row,
                    signal.severity,
                    "failure" if signal.category == "bug" else signal.category,
                    signal.description,
                )
            is_new, repeat_count = self.intelligence.record_event(event)
            if not is_new:
                duplicate_events += 1
                continue
            new_events += 1
            if signal is None:
                continue
            job_id, payload = build_task(signal, repeat_count)
            try:
                self.task_store.enqueue(job_id, payload)
            except ValueError:
                # The deterministic job ID already exists; treat it as idempotent.
                continue
            tasks_created += 1
            job_ids.append(job_id)
        if newest_id is not None:
            self.intelligence.set_checkpoint(newest_id)
        return CollectorReport(
            fetched, accepted, ignored, new_events, duplicate_events, tasks_created, tuple(job_ids)
        )

    @staticmethod
    def _event(
        row: dict[str, object], severity: str, category: str, message: str
    ) -> N8NExecutionEvent:
        execution_id = str(row.get("id") or "unknown")
        workflow_id = str(row.get("workflowId") or "unknown")
        workflow_name = str(row.get("workflowName") or workflow_id)
        status = str(row.get("status") or "unknown")
        observed_at = str(row.get("stoppedAt") or row.get("startedAt") or "unknown")
        return N8NExecutionEvent(
            event_id=fingerprint_execution(row),
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_name=sanitize_message(workflow_name)[:200],
            status=status,
            severity=severity,
            category=category,
            message=sanitize_message(message),
            observed_at=observed_at,
            metadata={"mode": sanitize_message(str(row.get("mode") or "unknown"))[:80]},
        )


def default_database() -> Path:
    return Path(os.getenv("N8N_INTEL_DATABASE", "/var/lib/cknexus/n8n-intelligence/events.db"))
