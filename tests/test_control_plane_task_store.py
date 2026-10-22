from __future__ import annotations

import json
import sqlite3

import pytest

from creator_app.control_plane.task_store import TaskStore


def test_task_store_persists_checkpoint_and_result(tmp_path) -> None:
    db_path = tmp_path / "tasks.sqlite3"
    store = TaskStore(db_path)
    store.enqueue("job-1", {"description": "verify MCP", "priority": 1})

    claimed = store.claim_next("worker-a", lease_seconds=60)
    assert claimed is not None
    assert claimed["job_id"] == "job-1"
    assert claimed["state"] == "running"
    assert db_path.stat().st_mode & 0o777 == 0o600

    token = claimed["lease_token"]
    assert token
    store.save_checkpoint(
        "job-1",
        {"stage": "tests", "completed": ["unit"]},
        worker_id="worker-a",
        lease_token=token,
    )
    store.finish(
        "job-1", success=True, result={"passed": 8}, worker_id="worker-a", lease_token=token
    )

    reopened = TaskStore(db_path)
    item = reopened.get("job-1")
    assert item is not None
    assert item["state"] == "completed"
    assert json.loads(item["checkpoint_json"]) == {"stage": "tests", "completed": ["unit"]}
    assert json.loads(item["result_json"]) == {"passed": 8}


def test_expired_running_job_returns_to_queue(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-2", {"description": "resume after restart"})
    claimed = store.claim_next("worker-a", lease_seconds=0)
    assert claimed is not None

    assert store.requeue_expired() == 1
    recovered = store.claim_next("worker-b", lease_seconds=60)
    assert recovered is not None
    assert recovered["job_id"] == "job-2"
    assert recovered["attempts"] == 2


def test_duplicate_job_id_is_rejected(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-3", {"description": "one"})
    with pytest.raises(ValueError, match="already exists"):
        store.enqueue("job-3", {"description": "two"})


def test_claim_is_atomic_between_store_instances(tmp_path) -> None:
    db_path = tmp_path / "tasks.sqlite3"
    first = TaskStore(db_path)
    second = TaskStore(db_path)
    first.enqueue("job-4", {"description": "single claim"})

    claimed_first = first.claim_next("worker-a", lease_seconds=60)
    claimed_second = second.claim_next("worker-b", lease_seconds=60)
    assert claimed_first is not None
    assert claimed_second is None


def test_expired_job_is_failed_after_retry_budget_exhausted(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-retry-limit", {"description": "must not loop forever"})

    first = store.claim_next("worker-a", lease_seconds=0)
    assert first is not None
    assert store.requeue_expired(max_attempts=2) == 1

    second = store.claim_next("worker-b", lease_seconds=0)
    assert second is not None
    assert second["attempts"] == 2
    assert store.requeue_expired(max_attempts=2) == 0

    item = store.get("job-retry-limit")
    assert item is not None
    assert item["state"] == "failed"
    assert "retry budget exhausted" in item["error_text"]
    assert store.claim_next("worker-c") is None


def test_expired_lease_cannot_write_checkpoint_or_finish(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-expired", {"description": "expired worker must not commit"})
    claimed = store.claim_next("worker-a", lease_seconds=0)
    assert claimed is not None

    with pytest.raises(ValueError, match="not running with a valid lease"):
        store.save_checkpoint(
            "job-expired",
            {"stage": "late"},
            worker_id="worker-a",
            lease_token=claimed["lease_token"],
        )
    with pytest.raises(ValueError, match="not running with a valid lease"):
        store.finish(
            "job-expired",
            success=True,
            result={"late": True},
            worker_id="worker-a",
            lease_token=claimed["lease_token"],
        )


def test_requeue_expired_rejects_invalid_attempt_budget(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    for max_attempts in (0, -1, 11):
        with pytest.raises(ValueError, match="max_attempts must be between 1 and 10"):
            store.requeue_expired(max_attempts=max_attempts)


def test_stale_worker_cannot_write_after_job_is_reclaimed(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-fenced", {"description": "old worker must be fenced out"})

    first = store.claim_next("worker-a", lease_seconds=0)
    assert first is not None
    assert store.requeue_expired(max_attempts=3) == 1
    second = store.claim_next("worker-b", lease_seconds=60)
    assert second is not None
    assert second["worker_id"] == "worker-b"

    with pytest.raises(ValueError, match="valid lease"):
        store.save_checkpoint(
            "job-fenced", {"stage": "stale"}, worker_id="worker-a", lease_token=first["lease_token"]
        )
    with pytest.raises(ValueError, match="valid lease"):
        store.finish(
            "job-fenced", success=True, worker_id="worker-a", lease_token=first["lease_token"]
        )


def test_lease_token_fences_stale_worker_even_when_worker_id_is_reused(tmp_path) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-lease-token", {"description": "lease token fencing"})

    first = store.claim_next("worker-a", lease_seconds=0)
    assert first is not None
    old_token = first["lease_token"]
    assert old_token
    assert store.requeue_expired(max_attempts=3) == 1

    second = store.claim_next("worker-a", lease_seconds=60)
    assert second is not None
    assert second["lease_token"] != old_token

    with pytest.raises(ValueError, match="valid lease"):
        store.save_checkpoint(
            "job-lease-token", {"stage": "stale"}, worker_id="worker-a", lease_token=old_token
        )
    with pytest.raises(ValueError, match="valid lease"):
        store.finish("job-lease-token", success=True, worker_id="worker-a", lease_token=old_token)


def test_legacy_database_migrates_lease_token_and_status_hides_token(tmp_path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE control_plane_tasks (
                job_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('queued','running','completed','failed')),
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                worker_id TEXT,
                lease_until REAL,
                attempts INTEGER NOT NULL DEFAULT 0,
                checkpoint_json TEXT,
                result_json TEXT,
                error_text TEXT
            )
            """
        )

    store = TaskStore(db_path)
    store.enqueue("legacy-job", {"description": "migrate safely"})
    claimed = store.claim_next("worker-a", lease_seconds=60)
    assert claimed is not None
    assert claimed["lease_token"]
    status = store.get("legacy-job")
    assert status is not None
    assert "lease_token" not in status


@pytest.mark.parametrize("lease_seconds", [-1, 86401, float("inf"), float("nan")])
def test_claim_rejects_invalid_lease_duration(tmp_path, lease_seconds) -> None:
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.enqueue("job-bad-lease", {"description": "lease bounds"})

    with pytest.raises(ValueError, match="lease_seconds must be finite and between 0 and 86400"):
        store.claim_next("worker-a", lease_seconds=lease_seconds)
    assert store.get("job-bad-lease")["state"] == "queued"
