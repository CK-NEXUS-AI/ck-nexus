from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.agnes_experiential_memory import (
    ExperienceResult,
    ExperientialMemory,
    ValidityStatus,
)
from creator_app.agnes_ledger import AppendOnlyLedger


def memory(tmp_path: Path) -> ExperientialMemory:
    return ExperientialMemory(AppendOnlyLedger(tmp_path / "experience.jsonl"))


def record(
    store: ExperientialMemory,
    *,
    task_type: str = "analysis",
    lesson: str = "Prefer verified sources",
    confidence: float = 0.8,
    supersedes: str | None = None,
):
    return store.record_experience(
        task_type=task_type,
        context_digest=store.digest_context("private task context"),
        action_strategy="cross-check primary sources",
        result=ExperienceResult.SUCCESS,
        lesson=lesson,
        confidence=confidence,
        verified_by="independent_verifier",
        source_run="run_123",
        evidence_links=["evd_123"],
        supersedes=supersedes,
    )


def test_records_digest_only_and_preserves_hash_chain(tmp_path: Path):
    store = memory(tmp_path)
    entry = record(store)
    raw = store.ledger.path.read_text(encoding="utf-8")
    assert "private task context" not in raw
    assert entry.context_digest == store.digest_context("private task context")
    assert store.ledger.verify().valid is True


def test_retrieve_relevant_returns_only_valid_ranked_entries(tmp_path: Path):
    store = memory(tmp_path)
    low = record(store, confidence=0.2, lesson="low confidence")
    high = record(store, confidence=0.9, lesson="high confidence")
    store.invalidate_experience(
        low.experience_id, verified_by="verifier", reason="stale"
    )
    results = store.retrieve_relevant(task_type="analysis")
    assert [item.experience_id for item in results] == [high.experience_id]


def test_supersession_is_append_only_and_hides_old_entry_from_retrieval(tmp_path: Path):
    store = memory(tmp_path)
    old = record(store, lesson="old")
    new = record(store, lesson="new", supersedes=old.experience_id)
    graph = store.build_provenance_graph()
    nodes = {node["experience_id"]: node for node in graph["nodes"]}
    assert (
        nodes[old.experience_id]["provenance"]["validity_status"]
        == ValidityStatus.SUPERSEDED.value
    )
    assert (
        store.retrieve_relevant(task_type="analysis")[0].experience_id
        == new.experience_id
    )
    assert len(store.ledger.path.read_text(encoding="utf-8").splitlines()) == 3


def test_validate_provenance_appends_verification_event(tmp_path: Path):
    store = memory(tmp_path)
    entry = record(store)
    validated = store.validate_provenance(
        entry.experience_id, verified_by="human_governor", evidence_links=["evd_456"]
    )
    assert validated.last_validated
    assert validated.verified_by == "human_governor"
    assert validated.evidence_links == ("evd_456",)
    assert store.ledger.verify().entries == 2


def test_provenance_graph_links_run_evidence_and_supersession(tmp_path: Path):
    store = memory(tmp_path)
    old = record(store, lesson="old")
    new = record(store, lesson="new", supersedes=old.experience_id)
    graph = store.build_provenance_graph()
    edge_types = {edge["type"] for edge in graph["edges"]}
    assert {"SOURCE_RUN", "EVIDENCE", "SUPERSEDES"} <= edge_types
    assert graph["ledger"]["valid"] is True


def test_rejects_raw_or_malformed_context_instead_of_silently_storing_it(
    tmp_path: Path,
):
    store = memory(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        store.record_experience(
            task_type="analysis",
            context_digest="raw sensitive context",
            action_strategy="test",
            result="SUCCESS",
            lesson="test",
            confidence=0.5,
            verified_by="verifier",
        )


def test_tampered_ledger_fails_closed(tmp_path: Path):
    store = memory(tmp_path)
    record(store)
    rows = store.ledger.path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    payload["payload"]["lesson"] = "tampered"
    store.ledger.path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="integrity failure"):
        store.retrieve_relevant(task_type="analysis")


def test_agnes_cannot_self_verify_learning(tmp_path: Path):
    store = memory(tmp_path)
    with pytest.raises(ValueError, match="self-verify"):
        store.record_experience(
            task_type="analysis",
            context_digest=store.digest_context("context"),
            action_strategy="test",
            result="SUCCESS",
            lesson="test",
            confidence=0.5,
            verified_by="AGNES",
        )
