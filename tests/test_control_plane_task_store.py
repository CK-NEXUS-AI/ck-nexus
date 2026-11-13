from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from creator_app.control_plane.task_store import TaskStore
from creator_app.council_authority.identity import IdentityVerifier

_TEST_SECRET = "test_secret_key_must_be_at_least_32_bytes_long_ok"


@pytest.fixture(autouse=True)
def _isolate_identity_secret(monkeypatch):
    monkeypatch.setenv("CK_IDENTITY_SECRET", _TEST_SECRET)


def _test_approver_token():
    return IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="test-authority", agent_id="test-approver", role="admin"
    )


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
    with pytest.raises(PermissionError, match="task-bound Core/L3 capability grant"):
        store.finish(
            "job-1",
            success=True,
            result={"passed": 8},
            evidence_reference="evidence://job-1",
            approver_token=_test_approver_token(),
            worker_id="worker-a",
            lease_token=token,
        )

    reopened = TaskStore(db_path)
    item = reopened.get("job-1")
    assert item is not None
    assert item["state"] == "running"
    assert json.loads(item["checkpoint_json"]) == {"stage": "tests", "completed": ["unit"]}
    assert item["result_json"] is None


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
            evidence_reference="evidence://job-expired",
            approver_token=_test_approver_token(),
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
            "job-fenced",
            success=True,
            evidence_reference="evidence://job-fenced",
            approver_token=_test_approver_token(),
            worker_id="worker-a",
            lease_token=first["lease_token"],
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
        store.finish(
            "job-lease-token",
            success=True,
            evidence_reference="evidence://job-lease-token",
            approver_token=_test_approver_token(),
            worker_id="worker-a",
            lease_token=old_token,
        )


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


def test_has_open_tasks_tracks_queued_and_running_states(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.sqlite3")
    assert store.has_open_tasks() is False

    store.enqueue("open-task", {"handler": "test"})
    assert store.has_open_tasks() is True

    claimed = store.claim_next("test-worker", lease_seconds=60)
    assert claimed is not None
    assert store.has_open_tasks() is True

    with pytest.raises(PermissionError, match="task-bound Core/L3 capability grant"):
        store.finish(
            "open-task",
            success=True,
            result={},
            evidence_reference="evidence://open-task",
            approver_token=_test_approver_token(),
            worker_id="test-worker",
            lease_token=claimed["lease_token"],
        )
    assert store.has_open_tasks() is True


def test_task_bound_l3_grant_completes_and_consumes_atomically(tmp_path) -> None:
    import hashlib
    import hmac

    from creator_app.council_authority.storage import AuthorityStore

    db_path = tmp_path / "shared-authority-tasks.sqlite3"
    secret = b"completion-grant-secret-32-bytes-minimum"
    store = TaskStore(db_path, grant_secret=secret)
    authority = AuthorityStore(str(db_path))
    job_id = "job-l3-complete"
    evidence_ref = "evidence://job-l3-complete"
    store.enqueue(job_id, {"description": "verified completion"})
    claimed = store.claim_next("worker-l3", lease_seconds=60)
    assert claimed is not None
    authority.seed_evidence(
        ref=evidence_ref,
        kind="test_report",
        digest=hashlib.sha256(b"verified").hexdigest(),
        task_id=job_id,
        quality=1.0,
        verified=True,
    )
    params_hash = TaskStore._completion_params_hash(
        job_id, evidence_ref, {"verified": True, "evidence_reference": evidence_ref}
    )
    grant = authority.create_grant(
        agent_id="OWNER",
        capability_id="control_plane.task.complete",
        params_hash=params_hash,
        task_id=job_id,
        ttl_seconds=60,
    )
    signature = hmac.new(
        secret, json.dumps(grant, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
    ).hexdigest()
    signed_grant = {**grant, "signature": signature}

    store.finish(
        job_id,
        success=True,
        result={"verified": True},
        evidence_reference=evidence_ref,
        execution_grant=signed_grant,
        worker_id="worker-l3",
        lease_token=claimed["lease_token"],
    )

    task = store.get(job_id)
    assert task is not None and task["state"] == "completed"
    completed_result = json.loads(task["result_json"])
    assert completed_result["evidence_reference"] == evidence_ref
    assert completed_result["approver_id"] == "OWNER"
    checkpoint = json.loads(task["checkpoint_json"])
    assert checkpoint["state"] == "completed"
    assert checkpoint["evidence_reference"] == evidence_ref
    assert checkpoint["approver_id"] == "OWNER"
    with authority._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
    assert row["used"] == 1


@pytest.mark.parametrize(
    ("evidence_task_id", "verified"),
    [("another-task", True), ("job-l3-denied", False)],
)
def test_l3_completion_grant_rejects_wrong_task_or_unverified_evidence(
    tmp_path, evidence_task_id, verified
) -> None:
    import hashlib
    import hmac

    from creator_app.council_authority.storage import AuthorityStore

    db_path = tmp_path / "shared-authority.sqlite3"
    secret = b"completion-grant-secret-32-bytes-minimum"
    store = TaskStore(db_path, grant_secret=secret)
    authority = AuthorityStore(str(db_path))
    job_id = "job-l3-denied"
    evidence_ref = "evidence://unverified"
    store.enqueue(job_id, {"description": "must stay running"})
    claimed = store.claim_next("worker-l3", lease_seconds=60)
    assert claimed is not None
    authority.seed_evidence(
        ref=evidence_ref,
        kind="test_report",
        digest=hashlib.sha256(b"bad").hexdigest(),
        task_id=evidence_task_id,
        quality=1.0,
        verified=verified,
    )
    params_hash = TaskStore._completion_params_hash(
        job_id,
        evidence_ref,
        {"verified": True, "evidence_reference": evidence_ref},
    )
    grant = authority.create_grant(
        agent_id="OWNER",
        capability_id="control_plane.task.complete",
        params_hash=params_hash,
        task_id=job_id,
        ttl_seconds=60,
    )
    signature = hmac.new(
        secret, json.dumps(grant, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
    ).hexdigest()
    with pytest.raises(PermissionError, match="task-bound Core/L3 capability grant"):
        store.finish(
            job_id,
            success=True,
            result={"verified": True},
            evidence_reference=evidence_ref,
            execution_grant={**grant, "signature": signature},
            worker_id="worker-l3",
            lease_token=claimed["lease_token"],
        )
    task = store.get(job_id)
    assert task is not None and task["state"] == "running" and task["result_json"] is None
    with authority._db() as db:
        row = db.execute(
            "SELECT used FROM grants WHERE grant_id=?", (grant["grant_id"],)
        ).fetchone()
    assert row["used"] == 0


def test_pending_approval_resumes_only_with_task_bound_l3_grant(tmp_path) -> None:
    import hashlib
    import hmac

    from creator_app.council_authority.storage import AuthorityStore

    db_path = tmp_path / "pending-approval.sqlite3"
    secret = b"completion-grant-secret-32-bytes-minimum"
    store = TaskStore(db_path, grant_secret=secret)
    authority = AuthorityStore(str(db_path))
    job_id = "job-pending-approval"
    evidence_ref = "evidence://pending-approval"
    store.enqueue(job_id, {"description": "await owner approval"})
    claimed = store.claim_next("worker", lease_seconds=60)
    assert claimed is not None
    store.request_approval(
        job_id,
        result={"tests_ok": True},
        evidence_reference=evidence_ref,
        worker_id="worker",
        lease_token=claimed["lease_token"],
    )
    pending = store.get(job_id)
    assert pending is not None and pending["state"] == "awaiting_approval"
    assert store.has_open_tasks() is True

    authority.seed_evidence(
        ref=evidence_ref,
        kind="test_report",
        digest=hashlib.sha256(b"ok").hexdigest(),
        task_id=job_id,
        quality=1.0,
        verified=True,
    )
    grant = authority.create_grant(
        agent_id="OWNER",
        capability_id="control_plane.task.complete",
        params_hash=TaskStore._completion_params_hash(
            job_id, evidence_ref, {"tests_ok": True, "evidence_reference": evidence_ref}
        ),
        task_id=job_id,
        ttl_seconds=60,
    )
    signature = hmac.new(
        secret, json.dumps(grant, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256
    ).hexdigest()
    store.approve_pending_completion(
        job_id,
        execution_grant={**grant, "signature": signature},
        evidence_reference=evidence_ref,
    )
    completed = store.get(job_id)
    assert completed is not None and completed["state"] == "completed"
    completed_result = json.loads(completed["result_json"])
    assert completed_result["approver_id"] == "OWNER"
    checkpoint = json.loads(completed["checkpoint_json"])
    assert checkpoint["state"] == "completed"
    assert checkpoint["evidence_reference"] == evidence_ref
    assert checkpoint["approver_id"] == "OWNER"
    assert store.has_open_tasks() is False


def test_old_task_database_migrates_to_approval_state_without_data_loss(tmp_path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE control_plane_tasks (
            job_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('queued','running','completed','failed')),
            created_at REAL NOT NULL, updated_at REAL NOT NULL, worker_id TEXT,
            lease_until REAL, lease_token TEXT, attempts INTEGER NOT NULL DEFAULT 0,
            checkpoint_json TEXT, result_json TEXT, error_text TEXT
        )""")
        db.execute(
            "INSERT INTO control_plane_tasks("
            "job_id,payload_json,state,created_at,updated_at"
            ") VALUES('legacy','{}','queued',1,1)"
        )
    store = TaskStore(db_path)
    item = store.get("legacy")
    assert item is not None and item["state"] == "queued"
    with store._connect() as db:
        schema = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='control_plane_tasks'"
        ).fetchone()[0]
    assert "awaiting_approval" in schema
