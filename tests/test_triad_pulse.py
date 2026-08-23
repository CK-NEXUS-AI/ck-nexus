from dataclasses import replace
from hashlib import sha256

import pytest

from creator_app.cognitive_runtime.triad_evidence import (
    EvidenceEvaluationReceipt,
    EvidenceVerdict,
)
from creator_app.cognitive_runtime.triad_pulse import (
    PulseKind,
    TriadPulseEngine,
    TriadPulseError,
    TriadPulsePolicy,
)
from creator_app.cognitive_runtime.triad_scheduler import TriadRole

SUBJECT = "4f487a4d71580f630a428955e0a9d7b81060b398"


def digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def receipt(
    ordinal: int,
    *,
    verdict: EvidenceVerdict = EvidenceVerdict.MEASURED_NOT_VERIFIED,
    score_bps: int = 8000,
) -> EvidenceEvaluationReceipt:
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
        verdict=verdict,
        score_bps=score_bps,
        supporting_evidence_ids=(f"evidence-{ordinal}",),
        contradicting_evidence_ids=(),
        independent_publishers=2,
        critique_count=1,
        reasons=(),
    )


def ingest_range(engine: TriadPulseEngine, start: int, end: int):
    emitted = []
    for ordinal in range(start, end + 1):
        emitted.extend(engine.ingest(receipt(ordinal)))
    return tuple(emitted)


def test_review_pulse_emits_exactly_at_15() -> None:
    engine = TriadPulseEngine(SUBJECT)
    assert ingest_range(engine, 1, 14) == ()

    emitted = engine.ingest(receipt(15))

    assert len(emitted) == 1
    pulse = emitted[0]
    assert pulse.kind is PulseKind.REVIEW_15
    assert pulse.ordinal == 15
    assert pulse.window_start == 1
    assert pulse.window_end == 15
    assert pulse.window_size == 15
    assert pulse.measured_count == 15
    assert pulse.measured_ratio_bps == 10_000
    assert pulse.learning_consolidation_candidate is False
    assert pulse.verification_ceiling == "ADVISORY_ONLY"
    assert pulse.promotion_allowed is False
    assert pulse.external_action_allowed is False
    assert pulse.production_mutation_allowed is False


def test_consolidation_candidate_pulse_emits_exactly_at_20() -> None:
    engine = TriadPulseEngine(SUBJECT)
    ingest_range(engine, 1, 19)

    emitted = engine.ingest(receipt(20))

    assert len(emitted) == 1
    pulse = emitted[0]
    assert pulse.kind is PulseKind.CONSOLIDATE_20
    assert pulse.ordinal == 20
    assert pulse.window_start == 1
    assert pulse.window_end == 20
    assert pulse.window_size == 20
    assert pulse.learning_consolidation_candidate is True
    assert pulse.promotion_allowed is False


def test_lcm_60_emits_review_then_consolidation() -> None:
    engine = TriadPulseEngine(SUBJECT)
    ingest_range(engine, 1, 59)

    emitted = engine.ingest(receipt(60))

    assert tuple(pulse.kind for pulse in emitted) == (
        PulseKind.REVIEW_15,
        PulseKind.CONSOLIDATE_20,
    )
    assert emitted[0].window_start == 46
    assert emitted[1].window_start == 41


def test_pulse_window_preserves_negative_verdict_metrics() -> None:
    engine = TriadPulseEngine(SUBJECT)
    for ordinal in range(1, 12):
        engine.ingest(receipt(ordinal, score_bps=8000))
    engine.ingest(receipt(12, verdict=EvidenceVerdict.BLOCKED, score_bps=0))
    engine.ingest(receipt(13, verdict=EvidenceVerdict.CONTRADICTED, score_bps=0))
    engine.ingest(receipt(14, verdict=EvidenceVerdict.REJECTED, score_bps=0))

    pulse = engine.ingest(receipt(15, score_bps=6000))[0]

    assert pulse.measured_count == 12
    assert pulse.blocked_count == 1
    assert pulse.contradicted_count == 1
    assert pulse.rejected_count == 1
    assert pulse.measured_ratio_bps == 8000
    assert pulse.mean_score_bps == 6266


def test_duplicate_receipt_is_idempotent_and_does_not_advance() -> None:
    engine = TriadPulseEngine(SUBJECT)
    first = receipt(1)

    assert engine.ingest(first) == ()
    assert engine.ingest(first) == ()
    assert len(engine.records) == 1


def test_same_candidate_with_conflicting_receipt_fails_closed() -> None:
    engine = TriadPulseEngine(SUBJECT)
    first = receipt(1)
    engine.ingest(first)
    changed = replace(first, score_bps=7000)

    with pytest.raises(TriadPulseError, match="candidate_receipt_conflict"):
        engine.ingest(changed)


def test_receipt_authority_boundary_is_fail_closed() -> None:
    engine = TriadPulseEngine(SUBJECT)

    with pytest.raises(TriadPulseError, match="receipt_subject_mismatch"):
        engine.ingest(replace(receipt(1), subject_sha="other"))
    with pytest.raises(TriadPulseError, match="receipt_evaluator_role_invalid"):
        engine.ingest(replace(receipt(2), evaluator_role=TriadRole.BUILDER))
    with pytest.raises(TriadPulseError, match="receipt_verification_ceiling_invalid"):
        engine.ingest(replace(receipt(3), verification_ceiling="VERIFIED"))
    with pytest.raises(
        TriadPulseError,
        match="receipt_independent_verification_required",
    ):
        engine.ingest(replace(receipt(4), independent_verification_required=False))


def test_snapshot_replay_is_deterministic() -> None:
    engine = TriadPulseEngine(SUBJECT)
    ingest_range(engine, 1, 40)
    snapshot = engine.snapshot()

    TriadPulseEngine.verify_snapshot(
        snapshot,
        expected_subject_sha=SUBJECT,
        expected_head_digest=snapshot.head_digest,
    )

    assert tuple(pulse.ordinal for pulse in snapshot.pulses) == (15, 20, 30, 40)
    assert tuple(pulse.kind for pulse in snapshot.pulses) == (
        PulseKind.REVIEW_15,
        PulseKind.CONSOLIDATE_20,
        PulseKind.REVIEW_15,
        PulseKind.CONSOLIDATE_20,
    )


def test_snapshot_detects_outer_record_tampering_first() -> None:
    engine = TriadPulseEngine(SUBJECT)
    engine.ingest(receipt(1))
    snapshot = engine.snapshot()
    record = snapshot.records[0]
    tampered_record = replace(
        record,
        receipt_json=record.receipt_json.replace(
            '"score_bps":8000',
            '"score_bps":9000',
        ),
    )
    tampered = replace(snapshot, records=(tampered_record,))

    with pytest.raises(TriadPulseError, match="record_digest_mismatch"):
        TriadPulseEngine.verify_snapshot(
            tampered,
            expected_subject_sha=SUBJECT,
            expected_head_digest=snapshot.head_digest,
        )


def test_snapshot_detects_inner_receipt_tamper_after_record_reseal() -> None:
    engine = TriadPulseEngine(SUBJECT)
    engine.ingest(receipt(1))
    snapshot = engine.snapshot()
    record = snapshot.records[0]
    tampered_record = replace(
        record,
        receipt_json=record.receipt_json.replace(
            '"score_bps":8000',
            '"score_bps":9000',
        ),
        record_digest="",
    )
    tampered_record = replace(
        tampered_record,
        record_digest=tampered_record.recompute_digest(),
    )
    tampered = replace(
        snapshot,
        records=(tampered_record,),
        head_digest=tampered_record.record_digest,
    )

    with pytest.raises(TriadPulseError, match="receipt_payload_digest_mismatch"):
        TriadPulseEngine.verify_snapshot(
            tampered,
            expected_subject_sha=SUBJECT,
            expected_head_digest=tampered.head_digest,
        )


def test_snapshot_detects_pulse_replay_tampering() -> None:
    engine = TriadPulseEngine(SUBJECT)
    ingest_range(engine, 1, 20)
    snapshot = engine.snapshot()
    bad_pulse = replace(snapshot.pulses[0], measured_count=14)
    tampered = replace(snapshot, pulses=(bad_pulse, *snapshot.pulses[1:]))

    with pytest.raises(TriadPulseError, match="snapshot_pulse_replay_mismatch"):
        TriadPulseEngine.verify_snapshot(
            tampered,
            expected_subject_sha=SUBJECT,
            expected_head_digest=snapshot.head_digest,
        )


def test_invalid_pulse_policy_fails_closed() -> None:
    with pytest.raises(TriadPulseError, match="review_interval_invalid"):
        TriadPulsePolicy(review_every=0).validate()
    with pytest.raises(TriadPulseError, match="consolidation_interval_invalid"):
        TriadPulsePolicy(consolidate_every=0).validate()
    with pytest.raises(TriadPulseError, match="pulse_intervals_must_differ"):
        TriadPulsePolicy(review_every=15, consolidate_every=15).validate()
