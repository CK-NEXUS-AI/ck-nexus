from __future__ import annotations

import os
import time

import pytest

from creator_app.control_plane.task_store import TaskStore
from creator_app.control_plane.verification import ControlPlaneVerifier
from creator_app.control_plane.worker import RepairWorker
from creator_app.council_authority.identity import IdentityVerifier

_TEST_SECRET = "test_secret_key_must_be_at_least_32_bytes_long_ok"


@pytest.fixture(autouse=True)
def _isolate_identity_secret(monkeypatch):
    monkeypatch.setenv("CK_IDENTITY_SECRET", _TEST_SECRET)


def _test_approver_token():
    return IdentityVerifier(os.environ["CK_IDENTITY_SECRET"].encode()).issue(
        service_id="test-authority", agent_id="test-approver", role="admin"
    )


def test_worker_waits_for_approval_without_task_bound_grant(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "echo", "description": "safe canary"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=1),
        handlers={
            "echo": lambda payload: {
                "ok": True,
                "evidence_refs": ["evidence://job-1"],
                "evidence_reference": "evidence://job-1",
                "approver_token": _test_approver_token(),
            }
        },
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "awaiting_approval"
    assert result.release_evidence is False
    assert result.production_status == "NO-GO"
    assert result.external_mutation_authorized is False
    assert store.get("job-1")["state"] == "awaiting_approval"


def test_worker_handler_failure_is_bounded_and_failed(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "boom", "description": "safe canary"})

    def boom(_payload):
        raise RuntimeError("handler failure")

    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=1),
        handlers={"boom": boom},
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert result.release_evidence is False
    assert "handler failure" in (result.error or "")
    assert store.get("job-1")["state"] == "failed"


def test_worker_rejects_empty_evidence(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "empty", "description": "safe canary"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={"empty": lambda payload: {"ok": True, "evidence_refs": []}},
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert result.release_evidence is False
    assert store.get("job-1")["state"] == "failed"


def test_worker_repair_budget_is_bounded(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "repair", "description": "safe canary"})
    repair_calls: list[int] = []
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=2),
        handlers={
            "repair": lambda payload: {
                "ok": False,
                "evidence_refs": ["evidence://job-1"],
                "repair": lambda attempt: repair_calls.append(attempt),
            }
        },
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert result.release_evidence is False
    assert result.attempts == 3
    assert len(repair_calls) <= 2


def test_worker_has_no_production_authority(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "echo", "description": "safe canary"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={
            "echo": lambda payload: {
                "ok": True,
                "evidence_refs": ["evidence://job-1"],
                "evidence_reference": "evidence://job-1",
                "approver_token": _test_approver_token(),
            }
        },
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.production_status == "NO-GO"
    assert result.external_mutation_authorized is False


@pytest.mark.parametrize("payload", [{}, {"handler": "missing"}])
def test_worker_rejects_missing_handler_contract(tmp_path, payload):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", payload)
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={},
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert store.get("job-1")["state"] == "failed"


def test_orchestrator_queue_adapter_preserves_graph_metadata() -> None:
    from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator

    graph = ControlPlaneOrchestrator().plan("worker adapter")
    payloads = ControlPlaneOrchestrator().queue_payloads(graph)
    assert payloads[1]["node_id"] == "task-02-implementation"
    assert payloads[1]["depends_on"] == ["task-01-research"]
    assert all(item["production_status"] == "NO-GO" for item in payloads)
    assert all(item["external_mutation_authorized"] is False for item in payloads)


def test_worker_handler_timeout_fails(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "slow", "description": "safe canary"})

    def slow(_payload):
        time.sleep(0.2)
        return {"ok": True, "evidence_refs": ["evidence://job-1"]}

    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={"slow": slow},
        worker_id="worker-1",
        execution_timeout=0.01,
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert "timeout" in (result.error or "")
    assert result.release_evidence is False


def test_worker_cannot_finish_after_lease_expiry(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "echo", "description": "safe canary"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={
            "echo": lambda payload: {
                "ok": True,
                "evidence_refs": ["evidence://job-1"],
                "evidence_reference": "evidence://job-1",
                "approver_token": _test_approver_token(),
            }
        },
        worker_id="worker-1",
        execution_timeout=1,
        lease_seconds=0,
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert store.get("job-1")["state"] == "running"


def test_worker_dispatches_successful_completion_with_task_bound_grant(tmp_path, monkeypatch):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-complete", {"handler": "echo"})
    captured = {}

    def finish(job_id, **kwargs):
        captured["job_id"] = job_id
        captured.update(kwargs)

    monkeypatch.setattr(store, "finish", finish)
    grant = {"grant_id": "test-grant", "signature": "test-signature"}
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={
            "echo": lambda _payload: {
                "ok": True,
                "evidence_refs": ["evidence://job-complete"],
                "evidence_reference": "evidence://job-complete",
                "execution_grant": grant,
            }
        },
        worker_id="worker-complete",
    )

    result = worker.run_once()

    assert result.state == "completed"
    assert captured["job_id"] == "job-complete"
    assert captured["success"] is True
    assert captured["execution_grant"] == grant
