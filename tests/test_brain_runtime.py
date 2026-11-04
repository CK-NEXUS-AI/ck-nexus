from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.brain import BrainJournal, BrainRuntime


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    payload = {
        "schema_version": "1.0.0",
        "artifacts": [
            {
                "id": "core",
                "name": "CK-NEXUS Core",
                "class": "core",
                "status": "present",
                "integration_point": "internal",
                "authority_scope": "L3",
            },
            {
                "id": "provider",
                "name": "Provider",
                "class": "ai_provider",
                "status": "partial",
                "integration_point": "gateway",
                "authority_scope": "NONE",
            },
        ],
    }
    (root / "config" / "capability_catalog.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def test_brain_status_composes_components_and_fails_closed(tmp_path):
    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path=tmp_path / "brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing",
    )
    status = brain.status()
    assert (
        status["brain_status"] == "ready_for_planning" and status["catalog"]["artifact_count"] == 2
    )
    assert (
        status["planner"]["execution_performed"] is False
        and status["authority"]["external_mutation_authorized"] is False
    )
    assert status["production_status"] == "NO-GO" and status["q10_status"] == "NOT_VERIFIED"


def test_brain_plan_never_executes_or_grants_authority(tmp_path):
    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path=tmp_path / "brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing",
    )
    result = brain.plan("Improve model fallback and verify tests", priority=2)
    assert result["execution_state"] == "PLANNED_NOT_EXECUTED" and len(result["plan"]["nodes"]) == 4
    assert result["external_mutation_authorized"] is False
    assert all(x["external_mutation_authorized"] is False for x in result["queue_payloads"])


def test_journal_stores_fingerprint_not_raw_task_and_never_claims_verification(tmp_path):
    db = tmp_path / "brain.sqlite3"
    journal = BrainJournal(db)
    task = "private prompt marker DO_NOT_PERSIST"
    result = journal.record_observation(
        task=task,
        outcome="reported_success",
        reason_code="tests_passed_reported",
        evidence_refs=["sha256:abc123"],
        metrics={"duration_ms": 120, "arbitrary_prompt": 999, "input_tokens": 20},
    )
    assert result["raw_task_stored"] is False and result["verification_claimed"] is False
    assert task.encode() not in db.read_bytes() and b"arbitrary_prompt" not in db.read_bytes()
    summary = journal.summary()
    assert summary["observation_count"] == 1 and summary["outcomes"]["reported_success"] == 1
    assert summary["self_reported_outcomes_are_verified"] is False


def test_improvement_proposals_remain_candidates_until_owner_review(tmp_path):
    journal = BrainJournal(tmp_path / "brain.sqlite3")
    item = journal.propose_improvement(
        candidate_type="retrieval_quality",
        title="Add multilingual semantic retrieval",
        rationale=(
            "Benchmark semantic retrieval against lexical baseline using a rights-cleared corpus."
        ),
        evidence_refs=["evidence:retrieval-benchmark-001"],
    )
    assert (
        item["state"] == "candidate"
        and item["owner_approval_required"] is True
        and item["auto_promotion"] is False
    )
    assert journal.summary()["pending_improvement_candidates"] == 1


def test_journal_rejects_untrusted_outcomes_and_secret_shaped_refs(tmp_path):
    journal = BrainJournal(tmp_path / "brain.sqlite3")
    with pytest.raises(ValueError):
        journal.record_observation(task="task", outcome="verified")
    with pytest.raises(ValueError):
        journal.record_observation(
            task="task", outcome="reported_success", evidence_refs=["ghp_" + "a" * 30]
        )


def test_brain_status_reports_optional_cloud_worker_without_granting_authority(tmp_path):
    class Worker:
        def status(self):
            return {
                "provider": "github_actions",
                "enabled": False,
                "configured": False,
                "external_mutation_authorized": False,
            }

    brain = BrainRuntime(
        root=_root(tmp_path),
        journal_path=tmp_path / "brain.sqlite3",
        task_db_path=tmp_path / "tasks.sqlite3",
        knowledge_db_path=tmp_path / "missing.sqlite3",
        evidence_dir=tmp_path / "missing",
        cloud_worker=Worker(),
    )
    status = brain.status()
    assert status["cloud_worker"]["provider"] == "github_actions"
    assert status["cloud_worker"]["enabled"] is False
    assert status["authority"]["external_mutation_authorized"] is False
    assert status["production_status"] == "NO-GO"
