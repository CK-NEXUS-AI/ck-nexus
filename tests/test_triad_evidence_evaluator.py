from dataclasses import replace
from hashlib import sha256

import pytest

from creator_app.cognitive_runtime.triad_debate import (
    CandidateCritique,
    CandidateProposal,
    CandidateStatus,
    CritiqueSeverity,
    DebateRound,
)
from creator_app.cognitive_runtime.triad_evidence import (
    EvidenceAssurance,
    EvidenceEvaluationError,
    EvidenceObservation,
    EvidenceRelation,
    EvidenceVerdict,
    PublisherAttestation,
    TriadEvidenceEvaluator,
)
from creator_app.cognitive_runtime.triad_memory import TriadMemoryStore
from creator_app.cognitive_runtime.triad_scheduler import TriadRole

SUBJECT = "e8ca3c6006e483330181daaeea756e4ed86eafc5"


def candidate() -> CandidateProposal:
    return CandidateProposal(
        candidate_id="candidate-1",
        task_id="task-1",
        subject_sha=SUBJECT,
        proposer_role=TriadRole.BUILDER,
        statement="adopt bounded evidence evaluator",
        rationale="measured evidence must remain below independent verification",
        expected_delta="deterministic evidence scoring",
        evidence_refs=("ev-1", "ev-2"),
        status=CandidateStatus.MEASURED_NOT_VERIFIED,
    )


def critique(
    severity: CritiqueSeverity = CritiqueSeverity.MEDIUM,
) -> CandidateCritique:
    return CandidateCritique(
        critique_id="critique-1",
        candidate_id="candidate-1",
        task_id="task-1",
        subject_sha=SUBJECT,
        critic_role=TriadRole.CRITIC,
        severity=severity,
        findings=("check source independence",),
    )


def snapshot(*, with_critique: bool = True, blocking: bool = False):
    item = candidate()
    critiques = ()
    if with_critique:
        severity = (
            CritiqueSeverity.BLOCKING
            if blocking
            else CritiqueSeverity.MEDIUM
        )
        critiques = (critique(severity),)
    debate = DebateRound(
        round_id="round-1",
        task_id="task-1",
        subject_sha=SUBJECT,
        candidates=(item,),
        critiques=critiques,
    )
    store = TriadMemoryStore(SUBJECT)
    store.append_round(debate, correlation_id="corr-1")
    return store.snapshot()


def observation(
    evidence_id: str,
    publisher_id: str,
    *,
    relation: EvidenceRelation = EvidenceRelation.SUPPORTS,
    assurance: EvidenceAssurance = EvidenceAssurance.MEASURED,
    quality: int = 80,
    safety_veto: bool = False,
) -> EvidenceObservation:
    return EvidenceObservation(
        evidence_id=evidence_id,
        subject_sha=SUBJECT,
        source_id=f"source-{evidence_id}",
        publisher_id=publisher_id,
        artifact_digest=f"digest-{evidence_id}",
        relation=relation,
        assurance=assurance,
        quality=quality,
        safety_veto=safety_veto,
    )


def supporting_evidence() -> tuple[EvidenceObservation, ...]:
    return (
        observation("ev-1", "publisher-a", quality=80),
        observation("ev-2", "publisher-b", quality=70),
    )


def publisher_attestations(*publisher_ids: str) -> tuple[PublisherAttestation, ...]:
    result: list[PublisherAttestation] = []
    seen: set[str] = set()
    for publisher_id in publisher_ids:
        if publisher_id in seen:
            continue
        seen.add(publisher_id)
        authority_id = f"authority-{publisher_id}"
        payload = f"{SUBJECT}|{publisher_id}|{authority_id}".encode()
        result.append(
            PublisherAttestation(
                publisher_id=publisher_id,
                authority_id=authority_id,
                subject_sha=SUBJECT,
                attestation_digest=sha256(payload).hexdigest(),
            )
        )
    return tuple(result)


def supporting_attestations() -> tuple[PublisherAttestation, ...]:
    return publisher_attestations("publisher-a", "publisher-b")


def test_evaluator_can_only_reach_measured_not_verified() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=supporting_evidence(),
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=supporting_attestations(),
    )

    assert receipt.verdict is EvidenceVerdict.MEASURED_NOT_VERIFIED
    assert receipt.verification_ceiling == "MEASURED_NOT_VERIFIED"
    assert receipt.independent_verification_required is True
    assert receipt.score_bps == 7500
    assert receipt.independent_publishers == 2
    assert receipt.critique_count == 1


def test_support_quorum_requires_publisher_attestations() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=supporting_evidence(),
        evaluator_identity="triad-evaluator-1",
    )

    assert receipt.verdict is EvidenceVerdict.BLOCKED
    assert "publisher_attestation_required" in receipt.reasons
    assert "independent_publishers_insufficient" in receipt.reasons


def test_contradiction_dominates_support_score() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    evidence = (
        observation("ev-1", "publisher-a"),
        observation(
            "ev-2",
            "publisher-b",
            relation=EvidenceRelation.CONTRADICTS,
        ),
    )
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=evidence,
        evaluator_identity="triad-evaluator-1",
    )

    assert receipt.verdict is EvidenceVerdict.CONTRADICTED
    assert receipt.score_bps == 0
    assert receipt.reasons == ("contradiction_dominates",)


def test_safety_veto_rejects_candidate() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    evidence = (
        observation("ev-1", "publisher-a", safety_veto=True),
        observation("ev-2", "publisher-b"),
    )
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=evidence,
        evaluator_identity="triad-evaluator-1",
    )

    assert receipt.verdict is EvidenceVerdict.REJECTED
    assert receipt.reasons == ("safety_veto",)


def test_missing_critique_blocks_promotion() -> None:
    memory = snapshot(with_critique=False)
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=supporting_evidence(),
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=supporting_attestations(),
    )

    assert receipt.verdict is EvidenceVerdict.BLOCKED
    assert "critique_required" in receipt.reasons


def test_blocking_critique_blocks_promotion() -> None:
    memory = snapshot(blocking=True)
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=supporting_evidence(),
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=supporting_attestations(),
    )

    assert receipt.verdict is EvidenceVerdict.BLOCKED
    assert "blocking_critique" in receipt.reasons


def test_independent_publisher_quorum_is_required() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    evidence = (
        observation("ev-1", "same-publisher"),
        observation("ev-2", "same-publisher"),
    )
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=evidence,
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=publisher_attestations("same-publisher"),
    )

    assert receipt.verdict is EvidenceVerdict.BLOCKED
    assert "independent_publishers_insufficient" in receipt.reasons


def test_untrusted_support_does_not_count_as_support() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    evidence = (
        observation(
            "ev-1",
            "publisher-a",
            assurance=EvidenceAssurance.UNTRUSTED,
        ),
        observation("ev-2", "publisher-b"),
    )
    receipt = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=evidence,
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=supporting_attestations(),
    )

    assert receipt.verdict is EvidenceVerdict.BLOCKED
    assert "supporting_evidence_insufficient" in receipt.reasons


def test_wrong_evaluator_role_fails_closed() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    with pytest.raises(
        EvidenceEvaluationError,
        match="evaluator_role_not_allowed",
    ):
        evaluator.evaluate(
            candidate(),
            snapshot=memory,
            expected_memory_head_digest=memory.head_digest,
            evidence=supporting_evidence(),
            evaluator_identity="builder-1",
            evaluator_role=TriadRole.BUILDER,
        )


def test_stale_memory_head_is_rejected() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    with pytest.raises(Exception, match="snapshot_head_mismatch"):
        evaluator.evaluate(
            candidate(),
            snapshot=memory,
            expected_memory_head_digest="0" * 64,
            evidence=supporting_evidence(),
            evaluator_identity="triad-evaluator-1",
        )


def test_candidate_must_match_exact_memory_artifact() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    changed = replace(candidate(), expected_delta="different delta")
    with pytest.raises(
        EvidenceEvaluationError,
        match="candidate_memory_digest_mismatch",
    ):
        evaluator.evaluate(
            changed,
            snapshot=memory,
            expected_memory_head_digest=memory.head_digest,
            evidence=supporting_evidence(),
            evaluator_identity="triad-evaluator-1",
        )


def test_receipt_digest_is_independent_of_evidence_input_order() -> None:
    memory = snapshot()
    evaluator = TriadEvidenceEvaluator(SUBJECT)
    left = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=supporting_evidence(),
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=supporting_attestations(),
    )
    right = evaluator.evaluate(
        candidate(),
        snapshot=memory,
        expected_memory_head_digest=memory.head_digest,
        evidence=tuple(reversed(supporting_evidence())),
        evaluator_identity="triad-evaluator-1",
        publisher_attestations=tuple(reversed(supporting_attestations())),
    )

    assert left == right
    assert left.canonical_digest() == right.canonical_digest()
