from __future__ import annotations

import os

import pytest

from creator_app.control_plane.task_store import TaskStore
from creator_app.council_authority.identity import IdentityVerifier
from creator_app.control_plane.verification import VerificationResult
from creator_app.control_plane.worker import RepairWorker


_TEST_SECRET = 'test_secret_key_must_be_at_least_32_bytes_long_ok'
os.environ.setdefault("CK_IDENTITY_SECRET", _TEST_SECRET)


def _test_approver_token():
    return IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="test-authority", agent_id="test-approver", role="admin"
    )


class AlwaysVerified:
    max_repairs = 0

    def evaluate(self, **_kwargs):
        return VerificationResult(
            state="VERIFIED",
            attempts=1,
            evidence_refs=("evidence://synthetic-verifier-fixture",),
            release_evidence=True,
        )

    def repair_loop(self, **_kwargs):
        raise AssertionError("repair_loop must not run in this reproduction")


class PermissiveStore:
    """Isolate the worker default from TaskStore's independent approval guard."""

    def __init__(self):
        self.finished_result = None

    def claim_next(self, worker_id, *, lease_seconds, job_id):
        return {
            "job_id": job_id,
            "lease_token": "test-lease",
            "payload_json": {"handler": "empty-output"},
        }

    def save_checkpoint(self, *_args, **_kwargs):
        return None

    def finish(self, _job_id, *, success, result, **_kwargs):
        self.finished_result = {"success": success, **(result or {})}


def test_a_missing_release_evidence_field_must_not_default_to_true():
    store = PermissiveStore()
    worker = RepairWorker(
        store=store,
        verifier=AlwaysVerified(),
        handlers={"empty-output": lambda _payload: {}},
        worker_id="p0-test-worker",
    )

    result = worker.run_once(job_id="p0-worker-missing-field")

    assert result.release_evidence is False
    assert store.finished_result is not None
    assert store.finished_result["release_evidence"] is False


def test_b_finish_success_requires_evidence_reference_and_approver_token(tmp_path):
    store = TaskStore(tmp_path / "finish.sqlite3")
    store.enqueue("p0-finish-missing-approval", {"description": "P0 reproduction"})
    claimed = store.claim_next("p0-test-worker", lease_seconds=60)
    assert claimed is not None

    with pytest.raises(PermissionError, match="approver token"):
        store.finish(
            "p0-finish-missing-approval",
            success=True,
            result={"passed": True},
            worker_id="p0-test-worker",
            lease_token=claimed["lease_token"],
        )
    assert store.get("p0-finish-missing-approval")["state"] == "running"


def test_c_finish_rejects_forged_approver_identity(tmp_path):
    store = TaskStore(tmp_path / "forged-approver.sqlite3")
    store.enqueue("p0-forged-approver", {"description": "forged approver reproduction"})
    claimed = store.claim_next("untrusted-worker", lease_seconds=60)
    assert claimed is not None

    with pytest.raises(PermissionError, match="approver|authority|identity|service token"):
        store.finish(
            "p0-forged-approver",
            success=True,
            result={"passed": True},
            evidence_reference="evidence://synthetic-unverified",
            approver_token="untrusted-arbitrary-string",
            worker_id="untrusted-worker",
            lease_token=claimed["lease_token"],
        )


def test_d_finish_accepts_valid_approver_token(tmp_path):
    store = TaskStore(tmp_path / "valid-approver.sqlite3")
    store.enqueue("p0-valid-approver", {"description": "valid approver reproduction"})
    claimed = store.claim_next("trusted-worker", lease_seconds=60)
    assert claimed is not None
    token = IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="core-l3-test", agent_id="authorized-owner", role="admin"
    )

    store.finish(
        "p0-valid-approver",
        success=True,
        result={"passed": True},
        evidence_reference="evidence://verified-test-fixture",
        approver_token=token,
        worker_id="trusted-worker",
        lease_token=claimed["lease_token"],
    )
    completed = store.get("p0-valid-approver")
    assert completed is not None
    assert completed["state"] == "completed"
    import json
    stored = json.loads(completed["result_json"])
    assert stored["approver_id"] == "authorized-owner"
    assert stored["approver_role"] == "admin"


def test_e_finish_rejects_valid_non_admin_token(tmp_path):
    store = TaskStore(tmp_path / "non-admin.sqlite3")
    store.enqueue("p0-non-admin", {"description": "non-admin must not approve"})
    claimed = store.claim_next("worker", lease_seconds=60)
    assert claimed is not None
    token = IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="worker-service", agent_id="ordinary-agent", role="agent"
    )
    with pytest.raises(PermissionError, match="admin role"):
        store.finish(
            "p0-non-admin",
            success=True,
            result={},
            evidence_reference="evidence://test",
            approver_token=token,
            worker_id="worker",
            lease_token=claimed["lease_token"],
        )
