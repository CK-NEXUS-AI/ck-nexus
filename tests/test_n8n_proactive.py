import os
from datetime import UTC, datetime

from creator_app.control_plane.task_store import TaskStore
from creator_app.council_authority.identity import IdentityVerifier
from creator_app.n8n_intelligence.proactive import ProactiveTaskSeeder


_TEST_SECRET = 'test_secret_key_must_be_at_least_32_bytes_long_ok'
os.environ.setdefault("CK_IDENTITY_SECRET", _TEST_SECRET)


def _test_approver_token():
    return IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="test-authority", agent_id="test-approver", role="admin"
    )


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
        evidence_reference="evidence://n8n-proactive",
        approver_token=_test_approver_token(),
        worker_id="test-worker",
        lease_token=task["lease_token"],
    )

    result = seeder.run_once()

    assert result.state == "skipped"
    assert result.reason == "already_seeded_today"
