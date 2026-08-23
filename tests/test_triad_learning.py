from dataclasses import replace
from hashlib import sha256

import pytest

from creator_app.cognitive_runtime.triad_evidence import (
    EvidenceEvaluationReceipt,
    EvidenceVerdict,
)
from creator_app.cognitive_runtime.triad_learning import (
    LearningConsolidationError,
    LearningDecision,
    TriadLearningConsolidator,
)
from creator_app.cognitive_runtime.triad_pulse import (
    PulseKind,
    TriadPulseEngine,
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


def snapshot20(
    *,
    blocked: tuple[int, ...] = (),
    contradicted: tuple[int, ...] = (),
    rejected: tuple[int, ...] = (),
    score_bps: int = 8000,
):
    engine = TriadPulseEngine(SUBJECT)
    for ordinal in range(1, 21):
        verdict = EvidenceVerdict.MEASURED_NOT_VERIFIED
        score = score_bps
        if ordinal in blocked:
            verdict = EvidenceVerdict.BLOCKED
            score = 0
        elif ordinal in contradicted:
            verdict = EvidenceVerdict.CONTRADICTED
            score = 0
        elif ordinal in rejected:
            verdict = EvidenceVerdict.REJECTED
            score = 0
        engine.ingest(receipt(ordinal, verdict=verdict, score_bps=score))
    snapshot = engine.snapshot()
    pulse = next(
        item for item in snapshot.pulses if item.kind is PulseKind.CONSOLIDATE_20
    )
    return snapshot, pulse


def propose(
    consolidator: TriadLearningConsolidator,
    snapshot,
    pulse,
    *,
    capability: str = "retrieval-quality",
    insight: str = "rerank evidence before long-context assembly",
    expected_delta: str = "improve grounded retrieval precision",
    **kwargs,
):
    return consolidator.consolidate(
        snapshot=snapshot,
        expected_pulse_head_digest=snapshot.head_digest,
        source_pulse_id=pulse.pulse_id,
        capability=capability,
        insight=insight,
        expected_delta=expected_delta,
        **kwargs,
    )


def test_good_20_pulse_proposes_non_active_learning_candidate() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)

    result = propose(consolidator, snapshot, pulse)

    assert result.decision is LearningDecision.PROPOSE
    assert result.candidate is not None
    candidate = result.candidate
    assert candidate.source_pulse_id == pulse.pulse_id
    assert candidate.source_pulse_digest == pulse.canonical_digest()
    assert candidate.source_window_digest == pulse.window_digest
    assert len(candidate.source_receipt_digests) == 20
    assert candidate.verification_ceiling == "MEASURED_NOT_VERIFIED"
    assert candidate.independent_verification_required is True
    assert candidate.experiment_required is True
    assert candidate.adoption_allowed is False
    assert candidate.auto_activation_allowed is False
    assert candidate.external_action_allowed is False
    assert candidate.production_mutation_allowed is False


def test_review_15_pulse_cannot_drive_learning_consolidation() -> None:
    snapshot, _ = snapshot20()
    review = next(item for item in snapshot.pulses if item.kind is PulseKind.REVIEW_15)
    consolidator = TriadLearningConsolidator(SUBJECT)

    with pytest.raises(
        LearningConsolidationError,
        match="source_pulse_not_consolidation",
    ):
        propose(consolidator, snapshot, review)


def test_low_measured_ratio_blocks_candidate() -> None:
    snapshot, pulse = snapshot20(blocked=(1, 2, 3, 4, 5, 6))
    consolidator = TriadLearningConsolidator(SUBJECT)

    result = propose(consolidator, snapshot, pulse)

    assert result.decision is LearningDecision.BLOCK
    assert result.candidate is None
    assert "measured_ratio_below_threshold" in result.reasons


def test_low_mean_score_blocks_candidate() -> None:
    snapshot, pulse = snapshot20(score_bps=5500)
    consolidator = TriadLearningConsolidator(SUBJECT)

    result = propose(consolidator, snapshot, pulse)

    assert result.decision is LearningDecision.BLOCK
    assert result.candidate is None
    assert result.reasons == ("mean_score_below_threshold",)


def test_contradiction_or_rejection_quarantines_learning() -> None:
    snapshot, pulse = snapshot20(contradicted=(3,), rejected=(7,))
    consolidator = TriadLearningConsolidator(SUBJECT)

    result = propose(consolidator, snapshot, pulse)

    assert result.decision is LearningDecision.QUARANTINE
    assert result.candidate is None
    assert result.reasons == (
        "contradiction_limit_exceeded",
        "rejection_limit_exceeded",
    )


def test_duplicate_delta_is_blocked_before_adoption() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)
    fingerprint = consolidator.semantic_fingerprint(
        "retrieval-quality",
        "rerank evidence before long-context assembly",
        "improve grounded retrieval precision",
    )

    result = propose(
        consolidator,
        snapshot,
        pulse,
        known_fingerprints=(fingerprint,),
    )

    assert result.decision is LearningDecision.BLOCK
    assert result.reasons == ("duplicate_learning_delta",)


def test_known_semantic_conflict_is_quarantined() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)
    fingerprint = consolidator.semantic_fingerprint(
        "retrieval-quality",
        "rerank evidence before long-context assembly",
        "improve grounded retrieval precision",
    )

    result = propose(
        consolidator,
        snapshot,
        pulse,
        conflicting_fingerprints=(fingerprint,),
    )

    assert result.decision is LearningDecision.QUARANTINE
    assert result.reasons == ("semantic_conflict",)


def test_same_semantic_delta_is_normalized_and_blocked_on_repeat() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)
    first = propose(consolidator, snapshot, pulse)

    second = propose(
        consolidator,
        snapshot,
        pulse,
        capability="  RETRIEVAL-quality ",
        insight="rerank   evidence before long-context assembly",
        expected_delta="Improve Grounded Retrieval Precision",
    )

    assert first.decision is LearningDecision.PROPOSE
    assert second.decision is LearningDecision.BLOCK
    assert second.reasons == ("duplicate_learning_delta",)


def test_supersession_requires_prior_learning_and_preserves_history() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)

    with pytest.raises(
        LearningConsolidationError,
        match="superseded_learning_missing",
    ):
        propose(
            consolidator,
            snapshot,
            pulse,
            expected_delta="new safe delta",
            supersedes_learning_id="missing-learning",
        )

    first = propose(consolidator, snapshot, pulse)
    assert first.candidate is not None
    second = propose(
        consolidator,
        snapshot,
        pulse,
        capability="retrieval-quality-v2",
        insight="rerank evidence with explicit contradiction quarantine",
        expected_delta="improve precision without hiding conflicting evidence",
        supersedes_learning_id=first.candidate.learning_id,
    )

    assert second.decision is LearningDecision.PROPOSE
    assert second.candidate is not None
    ledger = consolidator.ledger_snapshot()
    assert len(ledger.records) == 2
    assert ledger.records[1].supersedes_learning_id == first.candidate.learning_id
    assert ledger.records[0].learning_id == first.candidate.learning_id


def test_ledger_is_append_only_and_tamper_evident() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)
    first = propose(consolidator, snapshot, pulse)
    assert first.candidate is not None
    ledger = consolidator.ledger_snapshot()

    TriadLearningConsolidator.verify_ledger_snapshot(
        ledger,
        expected_subject_sha=SUBJECT,
        expected_head_digest=ledger.head_digest,
    )

    record = ledger.records[0]
    tampered_record = replace(record, candidate_digest=digest("tampered"))
    tampered = replace(ledger, records=(tampered_record,))
    with pytest.raises(
        LearningConsolidationError,
        match="ledger_record_digest_mismatch",
    ):
        TriadLearningConsolidator.verify_ledger_snapshot(
            tampered,
            expected_subject_sha=SUBJECT,
            expected_head_digest=ledger.head_digest,
        )


def test_pulse_snapshot_subject_and_head_are_authoritative() -> None:
    snapshot, pulse = snapshot20()
    consolidator = TriadLearningConsolidator(SUBJECT)

    with pytest.raises(Exception, match="snapshot_head_mismatch"):
        consolidator.consolidate(
            snapshot=snapshot,
            expected_pulse_head_digest="0" * 64,
            source_pulse_id=pulse.pulse_id,
            capability="retrieval-quality",
            insight="rerank evidence",
            expected_delta="improve precision",
        )
