from __future__ import annotations

import time

import pytest

from creator_app.control_plane.task_store import TaskStore
from creator_app.control_plane.verification import ControlPlaneVerifier
from creator_app.control_plane.worker import RepairWorker


def test_worker_executes_verifies_and_finishes(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-1", {"handler": "echo", "description": "safe canary"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=1),
        handlers={
            "echo": lambda payload: {
                "ok": True,
                "security_ok": True,
                "evidence_refs": ["evidence://job-1"],
            }
        },
        worker_id="worker-1",
    )
    result = worker.run_once()
    assert result.state == "completed"
    assert result.release_evidence is True
    assert result.production_status == "NO-GO"
    assert result.external_mutation_authorized is False
    assert store.get("job-1")["state"] == "completed"


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
                "security_ok": True,
                "evidence_refs": ["evidence://job-1"],
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
        return {"ok": True, "security_ok": True, "evidence_refs": ["evidence://job-1"]}

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
                "security_ok": True,
                "evidence_refs": ["evidence://job-1"],
            }
        },
        worker_id="worker-1",
        execution_timeout=1,
        lease_seconds=0,
    )
    result = worker.run_once()
    assert result.state == "failed"
    assert store.get("job-1")["state"] == "running"


def test_worker_requires_explicit_security_verification(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-security", {"handler": "echo"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={"echo": lambda payload: {
            "ok": True,
            "evidence_refs": ["evidence://job-security"],
        }},
        worker_id="worker-1",
    )

    result = worker.run_once()

    assert result.state == "failed"
    assert result.release_evidence is False
    assert store.get("job-security")["state"] == "failed"


def test_worker_rejects_string_instead_of_evidence_ref_collection(tmp_path):
    store = TaskStore(tmp_path / "queue.sqlite3")
    store.enqueue("job-evidence-type", {"handler": "echo"})
    worker = RepairWorker(
        store=store,
        verifier=ControlPlaneVerifier(max_repairs=0),
        handlers={"echo": lambda payload: {
            "ok": True,
            "security_ok": True,
            "evidence_refs": "evidence://job-evidence-type",
        }},
        worker_id="worker-1",
    )

    result = worker.run_once()

    assert result.state == "failed"
    assert result.release_evidence is False
    assert store.get("job-evidence-type")["state"] == "failed"
