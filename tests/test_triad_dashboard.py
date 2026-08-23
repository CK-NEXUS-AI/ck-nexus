import json
from dataclasses import replace
from hashlib import sha256

import pytest

from creator_app.cognitive_runtime.triad_dashboard import (
    TriadDashboardError,
    TriadDashboardProjector,
)
from creator_app.cognitive_runtime.triad_evidence import (
    EvidenceEvaluationReceipt,
    EvidenceVerdict,
)
from creator_app.cognitive_runtime.triad_learning import TriadLearningConsolidator
from creator_app.cognitive_runtime.triad_pulse import PulseKind, TriadPulseEngine
from creator_app.cognitive_runtime.triad_scheduler import TriadRole

SUBJECT = "4f487a4d71580f630a428955e0a9d7b81060b398"


def digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def receipt(ordinal: int) -> EvidenceEvaluationReceipt:
    candidate_id = f"candidate-{ordinal}"
    return EvidenceEvaluationReceipt(
        candidate_id=candidate_id,
        task_id=f"task-{ordinal}",
        subject_sha=SUBJECT,
        candidate_digest=digest(candidate_id),
        candidate_memory_id=f"memory-{ordinal}",
        memory_head_digest=digest(f"memory-head-{ordinal}"),
        evaluator_identity="triad-evaluator-1",
        evaluator_role=TriadRole.EVIDENCE_EVALUATOR,
        verdict=EvidenceVerdict.MEASURED_NOT_VERIFIED,
        score_bps=8000,
        supporting_evidence_ids=(f"evidence-{ordinal}",),
        contradicting_evidence_ids=(),
        independent_publishers=2,
        critique_count=1,
        reasons=(),
    )


def source_snapshots():
    pulse_engine = TriadPulseEngine(SUBJECT)
    for ordinal in range(1, 41):
        pulse_engine.ingest(receipt(ordinal))
    pulse_snapshot = pulse_engine.snapshot()
    consolidation_pulses = tuple(
        pulse
        for pulse in pulse_snapshot.pulses
        if pulse.kind is PulseKind.CONSOLIDATE_20
    )

    learner = TriadLearningConsolidator(SUBJECT)
    first = learner.consolidate(
        snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        source_pulse_id=consolidation_pulses[0].pulse_id,
        capability="retrieval-quality",
        insight="rerank evidence before long-context assembly",
        expected_delta="improve grounded retrieval precision",
    )
    assert first.candidate is not None
    second = learner.consolidate(
        snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        source_pulse_id=consolidation_pulses[1].pulse_id,
        capability="conflict-detection",
        insight="quarantine contradictory evidence before learning",
        expected_delta="reduce unsafe learning from conflicting claims",
        supersedes_learning_id=first.candidate.learning_id,
    )
    assert second.candidate is not None
    return pulse_snapshot, learner.ledger_snapshot()


def test_dashboard_projection_is_deterministic_and_read_only() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)

    left = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )
    right = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )

    assert left == right
    projector.verify_projection(left)
    assert left["authority"] == "READ_ONLY_PROJECTION"
    assert left["truth_state"] == "MEASURED_NOT_VERIFIED"
    assert left["independent_verification_required"] is True
    assert left["verified_claim_allowed"] is False
    assert left["mutation_allowed"] is False
    assert left["external_action_allowed"] is False
    assert left["production_mutation_allowed"] is False


def test_dashboard_exposes_bounded_metrics_without_raw_receipts() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)
    projection = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )

    pulse = projection["pipeline"]["pulse"]
    learning = projection["pipeline"]["learning"]
    assert pulse["receipt_count"] == 40
    assert pulse["review_15_count"] == 2
    assert pulse["consolidate_20_count"] == 2
    assert learning["proposal_count"] == 2
    assert learning["adoption_allowed"] is False
    assert learning["auto_activation_allowed"] is False

    serialized = json.dumps(projection, sort_keys=True)
    assert "receipt_json" not in serialized
    assert "evaluator_identity" not in serialized
    assert "rerank evidence before long-context assembly" not in serialized


def test_dashboard_privacy_contract_is_explicit() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)
    projection = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )

    assert projection["privacy"] == {
        "receipt_payloads_exposed": False,
        "hidden_reasoning_exposed": False,
        "credential_material_exposed": False,
    }


def test_dashboard_rejects_resealed_orphan_learning_source_pulse() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    first = learning_snapshot.records[0]
    orphan = replace(
        first,
        source_pulse_id="missing-pulse",
        record_digest="",
    )
    orphan = replace(orphan, record_digest=orphan.recompute_digest())
    second = learning_snapshot.records[1]
    second = replace(
        second,
        previous_record_digest=orphan.record_digest,
        record_digest="",
    )
    second = replace(second, record_digest=second.recompute_digest())
    tampered_learning = replace(
        learning_snapshot,
        records=(orphan, second),
        head_digest=second.record_digest,
    )
    projector = TriadDashboardProjector(SUBJECT)

    with pytest.raises(
        TriadDashboardError,
        match="learning_source_pulse_missing",
    ):
        projector.project(
            pulse_snapshot=pulse_snapshot,
            expected_pulse_head_digest=pulse_snapshot.head_digest,
            learning_snapshot=tampered_learning,
            expected_learning_head_digest=tampered_learning.head_digest,
        )


def test_dashboard_rejects_stale_source_heads() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)

    with pytest.raises(Exception, match="snapshot_head_mismatch"):
        projector.project(
            pulse_snapshot=pulse_snapshot,
            expected_pulse_head_digest="0" * 64,
            learning_snapshot=learning_snapshot,
            expected_learning_head_digest=learning_snapshot.head_digest,
        )
    with pytest.raises(Exception, match="ledger_head_mismatch"):
        projector.project(
            pulse_snapshot=pulse_snapshot,
            expected_pulse_head_digest=pulse_snapshot.head_digest,
            learning_snapshot=learning_snapshot,
            expected_learning_head_digest="0" * 64,
        )


def test_dashboard_projection_digest_detects_tampering() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)
    projection = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )
    tampered = dict(projection)
    tampered["pipeline"] = deepcopy = dict(projection["pipeline"])
    learning = dict(deepcopy["learning"])
    learning["proposal_count"] = 99
    deepcopy["learning"] = learning

    with pytest.raises(TriadDashboardError, match="projection_digest_mismatch"):
        projector.verify_projection(tampered)


def test_dashboard_cannot_claim_verified_or_mutation_authority() -> None:
    pulse_snapshot, learning_snapshot = source_snapshots()
    projector = TriadDashboardProjector(SUBJECT)
    projection = projector.project(
        pulse_snapshot=pulse_snapshot,
        expected_pulse_head_digest=pulse_snapshot.head_digest,
        learning_snapshot=learning_snapshot,
        expected_learning_head_digest=learning_snapshot.head_digest,
    )

    for field, value, error in (
        ("truth_state", "VERIFIED", "projection_truth_invalid"),
        ("verified_claim_allowed", True, "projection_verified_claim_forbidden"),
        ("mutation_allowed", True, "projection_mutation_allowed_forbidden"),
    ):
        tampered = dict(projection)
        tampered[field] = value
        with pytest.raises(TriadDashboardError, match=error):
            projector.verify_projection(tampered)
