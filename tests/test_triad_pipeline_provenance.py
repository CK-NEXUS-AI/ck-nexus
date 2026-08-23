from dataclasses import replace
from hashlib import sha256

import pytest

from creator_app.cognitive_runtime.triad_pipeline import (
    CANONICAL_STAGE_ORDER,
    TriadPipelineError,
    TriadPipelineLedger,
    TriadPipelineManifest,
    TriadPipelineStage,
    TriadStageBinding,
)

SUBJECT = "4f487a4d71580f630a428955e0a9d7b81060b398"
IMPLEMENTATION = "08325b77925f191c0609cb1b8ad86930324b93ed"


def digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def bindings(*, reverse: bool = False) -> tuple[TriadStageBinding, ...]:
    values = tuple(
        TriadStageBinding(
            stage=stage,
            subject_sha=SUBJECT,
            source_commit=(f"{index + 1:040x}"),
            artifact_digest=digest(stage.value),
        )
        for index, stage in enumerate(CANONICAL_STAGE_ORDER)
    )
    return tuple(reversed(values)) if reverse else values


def manifest(
    pipeline_id: str,
    *,
    parent: str = "",
    supersedes: str = "",
    fork_reason: str = "",
    reverse: bool = False,
) -> TriadPipelineManifest:
    return TriadPipelineManifest(
        pipeline_id=pipeline_id,
        subject_sha=SUBJECT,
        implementation_sha=IMPLEMENTATION,
        stages=bindings(reverse=reverse),
        parent_manifest_digest=parent,
        supersedes_manifest_digest=supersedes,
        fork_reason=fork_reason,
    )


def test_manifest_digest_is_deterministic_across_stage_input_order() -> None:
    left = manifest("pipeline-1")
    right = manifest("pipeline-1", reverse=True)
    assert left.canonical_digest() == right.canonical_digest()
    assert [item["stage"] for item in left.canonical_payload()["stages"]] == [
        stage.value for stage in CANONICAL_STAGE_ORDER
    ]


def test_manifest_binds_all_eight_stages_and_has_no_verified_authority() -> None:
    item = manifest("pipeline-1")
    payload = item.canonical_payload()
    assert len(payload["stages"]) == 8
    assert payload["truth_state"] == "MEASURED_NOT_VERIFIED"
    assert payload["independent_verification_required"] is True
    assert payload["verified_claim_allowed"] is False
    assert payload["adoption_allowed"] is False
    assert payload["mutation_allowed"] is False
    assert payload["production_promotion_allowed"] is False


def test_manifest_rejects_missing_or_duplicate_stage() -> None:
    base = manifest("pipeline-1")
    with pytest.raises(TriadPipelineError, match="pipeline_stage_count_invalid"):
        replace(base, stages=base.stages[:-1]).validate()

    duplicate = base.stages[:-1] + (base.stages[0],)
    with pytest.raises(TriadPipelineError, match="duplicate_pipeline_stage"):
        replace(base, stages=duplicate).validate()


def test_manifest_rejects_stage_subject_drift_and_bad_digest() -> None:
    base = manifest("pipeline-1")
    drifted = replace(base.stages[0], subject_sha="different")
    with pytest.raises(TriadPipelineError, match="stage_subject_mismatch"):
        replace(base, stages=(drifted,) + base.stages[1:]).validate()

    malformed = replace(base.stages[0], artifact_digest="not-a-digest")
    with pytest.raises(TriadPipelineError, match="stage_artifact_digest_invalid"):
        replace(base, stages=(malformed,) + base.stages[1:]).validate()


def test_manifest_rejects_self_promotion_or_mutation_flags() -> None:
    base = manifest("pipeline-1")
    verified = replace(base.stages[0], truth_state="VERIFIED")
    with pytest.raises(TriadPipelineError, match="stage_truth_state_invalid"):
        replace(base, stages=(verified,) + base.stages[1:]).validate()

    mutating = replace(base.stages[0], mutation_allowed=True)
    with pytest.raises(TriadPipelineError, match="stage_mutation_forbidden"):
        replace(base, stages=(mutating,) + base.stages[1:]).validate()

    promoted = replace(base.stages[0], production_promotion_allowed=True)
    with pytest.raises(TriadPipelineError, match="stage_production_promotion_forbidden"):
        replace(base, stages=(promoted,) + base.stages[1:]).validate()


def test_ledger_is_append_only_idempotent_and_replay_verifiable() -> None:
    ledger = TriadPipelineLedger(SUBJECT)
    first = manifest("pipeline-1")
    first_record = ledger.append(first)
    assert ledger.append(first) == first_record

    second = manifest(
        "pipeline-2",
        parent=first_record.manifest_digest,
        supersedes=first_record.manifest_digest,
    )
    ledger.append(second)
    snapshot = ledger.snapshot()

    TriadPipelineLedger.verify_snapshot(
        snapshot,
        expected_subject_sha=SUBJECT,
        expected_head_record_digest=snapshot.head_record_digest,
    )
    assert len(snapshot.records) == 2


def test_ledger_rejects_conflicting_identity_and_unknown_parent() -> None:
    ledger = TriadPipelineLedger(SUBJECT)
    original = manifest("pipeline-1")
    ledger.append(original)

    conflicting_binding = replace(
        original.stages[0],
        artifact_digest=digest("changed"),
    )
    conflicting = replace(
        original,
        stages=(conflicting_binding,) + original.stages[1:],
    )
    with pytest.raises(TriadPipelineError, match="pipeline_identity_conflict"):
        ledger.append(conflicting)

    with pytest.raises(TriadPipelineError, match="pipeline_parent_unknown"):
        ledger.append(manifest("pipeline-2", parent=digest("unknown")))


def test_fork_requires_reason_and_known_prior_parent() -> None:
    ledger = TriadPipelineLedger(SUBJECT)
    first = ledger.append(manifest("pipeline-1"))
    second = ledger.append(
        manifest("pipeline-2", parent=first.manifest_digest)
    )

    with pytest.raises(TriadPipelineError, match="pipeline_fork_reason_required"):
        ledger.append(manifest("pipeline-3", parent=first.manifest_digest))

    forked = ledger.append(
        manifest(
            "pipeline-3",
            parent=first.manifest_digest,
            supersedes=second.manifest_digest,
            fork_reason="bounded alternative candidate retained for comparison",
        )
    )
    assert forked.manifest.parent_manifest_digest == first.manifest_digest


def test_snapshot_detects_manifest_and_record_tampering() -> None:
    ledger = TriadPipelineLedger(SUBJECT)
    first = ledger.append(manifest("pipeline-1"))
    snapshot = ledger.snapshot()

    altered_binding = replace(
        first.manifest.stages[0],
        artifact_digest=digest("tampered"),
    )
    altered_manifest = replace(
        first.manifest,
        stages=(altered_binding,) + first.manifest.stages[1:],
    )
    altered_record = replace(first, manifest=altered_manifest)
    altered_snapshot = replace(snapshot, records=(altered_record,))
    with pytest.raises(TriadPipelineError, match="pipeline_manifest_digest_mismatch"):
        TriadPipelineLedger.verify_snapshot(
            altered_snapshot,
            expected_subject_sha=SUBJECT,
            expected_head_record_digest=snapshot.head_record_digest,
        )

    broken_record = replace(first, previous_record_digest=digest("bad-link"))
    broken_snapshot = replace(snapshot, records=(broken_record,))
    with pytest.raises(TriadPipelineError, match="pipeline_record_chain_invalid"):
        TriadPipelineLedger.verify_snapshot(
            broken_snapshot,
            expected_subject_sha=SUBJECT,
            expected_head_record_digest=snapshot.head_record_digest,
        )


def test_manifest_fork_reason_cannot_exist_without_parent() -> None:
    with pytest.raises(TriadPipelineError, match="fork_parent_required"):
        manifest("pipeline-1", fork_reason="orphan fork").validate()


def test_stage_enum_covers_declared_triad_sequence() -> None:
    assert CANONICAL_STAGE_ORDER == (
        TriadPipelineStage.EVENT_BUS,
        TriadPipelineStage.PARALLEL_SCHEDULER,
        TriadPipelineStage.DEBATE_CANDIDATE,
        TriadPipelineStage.TRIAD_MEMORY,
        TriadPipelineStage.EVIDENCE_EVALUATOR,
        TriadPipelineStage.PULSE_15_20,
        TriadPipelineStage.LEARNING_CONSOLIDATOR,
        TriadPipelineStage.DASHBOARD,
    )
