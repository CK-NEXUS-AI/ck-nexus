from dataclasses import replace

import pytest

from creator_app.cognitive_runtime.triad_debate import (
    CandidateCritique,
    CandidateProposal,
    CandidateStatus,
    CritiqueSeverity,
    DebateRound,
)
from creator_app.cognitive_runtime.triad_memory import (
    MemoryArtifactKind,
    TriadMemoryError,
    TriadMemorySnapshot,
    TriadMemoryStore,
)
from creator_app.cognitive_runtime.triad_scheduler import TriadRole

SUBJECT = "11059fb5e009484ce71cc5546b968e492dc2af19"


def candidate(
    candidate_id: str,
    *,
    revision: int = 1,
    parent: str = "",
    statement: str | None = None,
) -> CandidateProposal:
    return CandidateProposal(
        candidate_id=candidate_id,
        task_id="task-1",
        subject_sha=SUBJECT,
        proposer_role=TriadRole.BUILDER,
        statement=statement or f"proposal {candidate_id}",
        rationale=f"bounded rationale {candidate_id}",
        expected_delta=f"delta {candidate_id}",
        parent_candidate_id=parent,
        revision=revision,
        status=CandidateStatus.REVISED if revision > 1 else CandidateStatus.PROPOSED,
    )


def critique(critique_id: str, target: str) -> CandidateCritique:
    return CandidateCritique(
        critique_id=critique_id,
        candidate_id=target,
        task_id="task-1",
        subject_sha=SUBJECT,
        critic_role=TriadRole.CRITIC,
        severity=CritiqueSeverity.MEDIUM,
        findings=(f"finding for {target}",),
    )


def debate(*, reverse: bool = False) -> DebateRound:
    root = candidate("candidate-v1")
    revised = candidate("candidate-v2", revision=2, parent="candidate-v1")
    candidates = (revised, root) if reverse else (root, revised)
    return DebateRound(
        round_id="round-1",
        task_id="task-1",
        subject_sha=SUBJECT,
        candidates=candidates,
        critiques=(critique("critique-1", "candidate-v2"),),
    )


def test_round_append_builds_typed_causal_memory() -> None:
    store = TriadMemoryStore(SUBJECT)
    records = store.append_round(debate(), correlation_id="corr-1")

    assert [record.artifact_kind for record in records] == [
        MemoryArtifactKind.CANDIDATE,
        MemoryArtifactKind.CANDIDATE,
        MemoryArtifactKind.CRITIQUE,
        MemoryArtifactKind.ROUND,
    ]
    root, revised, critique_record, _round = records
    assert revised.causation_memory_id == root.memory_id
    assert revised.supersedes_memory_id == root.memory_id
    assert revised.parent_artifact_id == "candidate-v1"
    assert critique_record.causation_memory_id == revised.memory_id


def test_candidate_lineage_replays_root_to_latest_revision() -> None:
    store = TriadMemoryStore(SUBJECT)
    store.append_round(debate(), correlation_id="corr-1")

    lineage = store.lineage("candidate-v2")
    assert [record.artifact_id for record in lineage] == ["candidate-v1", "candidate-v2"]
    assert [record.revision for record in lineage] == [1, 2]


def test_snapshot_requires_exact_subject_and_sealed_head() -> None:
    store = TriadMemoryStore(SUBJECT)
    store.append_round(debate(), correlation_id="corr-1")
    snapshot = store.snapshot()

    TriadMemoryStore.verify_snapshot(
        snapshot,
        expected_subject_sha=SUBJECT,
        expected_head_digest=snapshot.head_digest,
    )
    with pytest.raises(TriadMemoryError, match="snapshot_subject_mismatch"):
        TriadMemoryStore.verify_snapshot(
            snapshot,
            expected_subject_sha="wrong-subject",
            expected_head_digest=snapshot.head_digest,
        )
    with pytest.raises(TriadMemoryError, match="snapshot_head_mismatch"):
        TriadMemoryStore.verify_snapshot(
            snapshot,
            expected_subject_sha=SUBJECT,
            expected_head_digest="0" * 64,
        )


def test_snapshot_detects_payload_tampering() -> None:
    store = TriadMemoryStore(SUBJECT)
    store.append_round(debate(), correlation_id="corr-1")
    snapshot = store.snapshot()
    first = replace(snapshot.records[0], payload_json='{"tampered":true}')
    forged = TriadMemorySnapshot(
        subject_sha=snapshot.subject_sha,
        head_digest=snapshot.head_digest,
        records=(first, *snapshot.records[1:]),
    )

    with pytest.raises(TriadMemoryError, match="record_payload_digest_mismatch"):
        TriadMemoryStore.verify_snapshot(
            forged,
            expected_subject_sha=SUBJECT,
            expected_head_digest=snapshot.head_digest,
        )


def test_append_is_idempotent_for_identical_artifacts() -> None:
    store = TriadMemoryStore(SUBJECT)
    first = store.append_round(debate(), correlation_id="corr-1")
    second = store.append_round(debate(), correlation_id="corr-1")

    assert second == first
    assert len(store.records) == 4


def test_same_artifact_identity_with_changed_content_fails_closed() -> None:
    store = TriadMemoryStore(SUBJECT)
    store.append_round(debate(), correlation_id="corr-1")
    changed = DebateRound(
        round_id="round-2",
        task_id="task-1",
        subject_sha=SUBJECT,
        candidates=(candidate("candidate-v1", statement="changed content"),),
    )

    with pytest.raises(TriadMemoryError, match="artifact_identity_conflict"):
        store.append_round(changed, correlation_id="corr-2")


def test_round_subject_mismatch_is_rejected() -> None:
    store = TriadMemoryStore("different-subject")
    with pytest.raises(TriadMemoryError, match="round_subject_mismatch"):
        store.append_round(debate(), correlation_id="corr-1")


def test_memory_digest_is_independent_of_debate_input_order() -> None:
    left = TriadMemoryStore(SUBJECT)
    right = TriadMemoryStore(SUBJECT)
    left.append_round(debate(), correlation_id="corr-1")
    right.append_round(debate(reverse=True), correlation_id="corr-1")

    assert left.snapshot().head_digest == right.snapshot().head_digest
    assert left.records == right.records


def test_snapshot_rejects_self_causation_even_with_recomputed_digest() -> None:
    store = TriadMemoryStore(SUBJECT)
    store.append_round(
        DebateRound(
            round_id="round-single",
            task_id="task-1",
            subject_sha=SUBJECT,
            candidates=(candidate("single"),),
        ),
        correlation_id="corr-single",
    )
    original = store.records[0]
    forged_record = replace(original, causation_memory_id=original.memory_id, record_digest="")
    forged_record = replace(forged_record, record_digest=forged_record.recompute_digest())
    snapshot = TriadMemorySnapshot(
        subject_sha=SUBJECT,
        head_digest=forged_record.record_digest,
        records=(forged_record,),
    )

    with pytest.raises(TriadMemoryError, match="causation_not_prior"):
        TriadMemoryStore.verify_snapshot(
            snapshot,
            expected_subject_sha=SUBJECT,
            expected_head_digest=forged_record.record_digest,
        )
