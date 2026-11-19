from dataclasses import dataclass
from pathlib import Path

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.collector import CollectorConfig, N8NIntelligenceCollector
from creator_app.n8n_intelligence.store import N8NIntelligenceStore


@dataclass
class FakeClient:
    rows: list[dict]
    failed: bool = False

    def list_executions(self, cursor=None):
        if self.failed:
            raise RuntimeError("upstream unavailable")
        return self.rows, None


def test_failed_execution_creates_one_idempotent_task(tmp_path: Path):
    rows = [
        {
            "id": "e1",
            "workflowId": "w1",
            "status": "error",
            "stoppedAt": "2026-10-24T00:00:00Z",
            "error": {"message": "boom"},
        }
    ]
    tasks = TaskStore(tmp_path / "tasks.db")
    intelligence = N8NIntelligenceStore(tmp_path / "events.db")
    collector = N8NIntelligenceCollector(FakeClient(rows), intelligence, tasks, CollectorConfig())
    first = collector.run_once()
    second = collector.run_once()
    assert first.tasks_created == 1
    assert second.tasks_created == 0
    assert tasks.get(first.job_ids[0]) is not None


def test_client_failure_creates_no_tasks(tmp_path: Path):
    tasks = TaskStore(tmp_path / "tasks.db")
    intelligence = N8NIntelligenceStore(tmp_path / "events.db")
    collector = N8NIntelligenceCollector(
        FakeClient([], failed=True), intelligence, tasks, CollectorConfig()
    )
    report = collector.run_once()
    assert report.tasks_created == 0
    assert report.error == "upstream_failure"
