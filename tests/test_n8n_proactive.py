from datetime import UTC, datetime

from creator_app.control_plane.task_store import TaskStore
from creator_app.n8n_intelligence.proactive import ProactiveTaskSeeder


def test_proactive_seeder_adds_one_bounded_low_risk_task(tmp_path):
    store = TaskStore(tmp_path / "tasks.sqlite3")
    seeder = ProactiveTaskSeeder(store, clock=lambda: datetime(2026, 10, 24, tzinfo=UTC))

    result = seeder.run_once()

    assert result.state == "seeded"
    task = store.peek_next()
    assert task["job_id"] == "n8n-proactive-2026-10-24"
    payload = __import__("json").loads(task["payload_json"])
    assert payload["handler"] == "n8n_development_signal"
    assert payload["production_status"] == "NO-GO"
    assert payload["external_mutation_authorized"] is False
    assert payload["source"] == "proactive_maintenance"


def test_proactive_seeder_does_not_compete_with_existing_work(tmp_path):
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("existing", {"handler": "other"})
    seeder = ProactiveTaskSeeder(store)

    result = seeder.run_once()

    assert result.state == "skipped"
    assert result.reason == "queue_not_empty"
    assert store.peek_next()["job_id"] == "existing"


def test_proactive_seeder_does_not_duplicate_same_day_task(tmp_path):
    store = TaskStore(tmp_path / "tasks.sqlite3")

    def clock():
        return datetime(2026, 10, 24, tzinfo=UTC)

    seeder = ProactiveTaskSeeder(store, clock=clock)
    assert seeder.run_once().state == "seeded"
    task = store.claim_next("test-worker", lease_seconds=60)
    store.finish(
        task["job_id"],
        success=True,
        result={},
        worker_id="test-worker",
        lease_token=task["lease_token"],
    )

    result = seeder.run_once()

    assert result.state == "skipped"
    assert result.reason == "already_seeded_today"


def test_proactive_seeder_retries_a_failed_daily_task_within_budget(tmp_path):
    store = TaskStore(tmp_path / "tasks.sqlite3")

    def clock():
        return datetime(2026, 10, 24, tzinfo=UTC)

    seeder = ProactiveTaskSeeder(store, clock=clock)
    assert seeder.run_once().state == "seeded"
    task = store.claim_next("test-worker", lease_seconds=60)
    store.finish(
        task["job_id"],
        success=False,
        error="assistant_timeout",
        worker_id="test-worker",
        lease_token=task["lease_token"],
    )

    result = seeder.run_once()

    assert result.state == "seeded"
    assert result.reason == "retrying_failed_task"
    assert store.peek_next()["job_id"] == "n8n-proactive-2026-10-24"
