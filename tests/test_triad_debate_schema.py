import pytest

from creator_app.cognitive_runtime.triad_debate import (
    CandidateCritique,
    CandidateProposal,
    CandidateStatus,
    CritiqueSeverity,
    DebateContractError,
    DebateRound,
)
from creator_app.cognitive_runtime.triad_scheduler import TriadRole

SUBJECT = "1aef07007c2b7c9783dde1dcb34a7b4b1d9e1dd8"


def candidate(candidate_id: str = "c1", **kwargs) -> CandidateProposal:
    values = {
        "candidate_id": candidate_id,
        "task_id": "task-1",
        "subject_sha": SUBJECT,
        "proposer_role": TriadRole.BUILDER,
        "statement": f"proposal-{candidate_id}",
        "rationale": "bounded deterministic rationale",
        "expected_delta": f"delta-{candidate_id}",
    }
    values.update(kwargs)
    return CandidateProposal(**values)


def critique(critique_id: str = "q1", candidate_id: str = "c1", **kwargs) -> CandidateCritique:
    values = {
        "critique_id": critique_id,
        "candidate_id": candidate_id,
        "task_id": "task-1",
        "subject_sha": SUBJECT,
        "critic_role": TriadRole.CRITIC,
        "severity": CritiqueSeverity.MEDIUM,
        "findings": (f"finding-{critique_id}",),
    }
    values.update(kwargs)
    return CandidateCritique(**values)


def test_round_digest_is_deterministic_across_input_order() -> None:
    c1 = candidate("c1")
    c2 = candidate("c2")
    q1 = critique("q1", "c1")
    q2 = critique("q2", "c2")
    left = DebateRound("round-1", "task-1", SUBJECT, (c1, c2), (q1, q2))
    right = DebateRound("round-1", "task-1", SUBJECT, (c2, c1), (q2, q1))
    assert left.canonical_digest() == right.canonical_digest()
    assert left.verification_ceiling == "MEASURED_NOT_VERIFIED"


def test_subject_mismatch_is_rejected() -> None:
    bad = candidate(subject_sha="wrong")
    with pytest.raises(DebateContractError, match="subject_mismatch"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_only_builder_can_propose() -> None:
    bad = candidate(proposer_role=TriadRole.CRITIC)
    with pytest.raises(DebateContractError, match="candidate_proposer_must_be_builder"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_only_critic_can_critique() -> None:
    bad = critique(critic_role=TriadRole.BUILDER)
    with pytest.raises(DebateContractError, match="critique_author_must_be_critic"):
        DebateRound("round-1", "task-1", SUBJECT, (candidate(),), (bad,)).validate()


def test_orphan_critique_is_rejected() -> None:
    bad = critique(candidate_id="missing")
    with pytest.raises(DebateContractError, match="critique_candidate_missing"):
        DebateRound("round-1", "task-1", SUBJECT, (candidate(),), (bad,)).validate()


def test_duplicate_candidate_id_is_rejected() -> None:
    with pytest.raises(DebateContractError, match="duplicate_candidate_id"):
        DebateRound("round-1", "task-1", SUBJECT, (candidate(), candidate())).validate()


def test_duplicate_candidate_semantics_is_rejected() -> None:
    c1 = candidate("c1", statement="same", expected_delta="same-delta")
    c2 = candidate("c2", statement="same", expected_delta="same-delta")
    with pytest.raises(DebateContractError, match="duplicate_candidate_semantics"):
        DebateRound("round-1", "task-1", SUBJECT, (c1, c2)).validate()


def test_revised_candidate_requires_parent() -> None:
    bad = candidate(status=CandidateStatus.REVISED, revision=2)
    with pytest.raises(DebateContractError, match="revised_candidate_parent_required"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_root_candidate_cannot_have_parent() -> None:
    bad = candidate(parent_candidate_id="c0")
    with pytest.raises(DebateContractError, match="root_candidate_parent_forbidden"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_revised_status_cannot_start_at_revision_one() -> None:
    bad = candidate(status=CandidateStatus.REVISED)
    with pytest.raises(DebateContractError, match="revised_candidate_revision_invalid"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_revision_parent_must_exist_in_same_round() -> None:
    bad = candidate("c2", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="missing")
    with pytest.raises(DebateContractError, match="candidate_parent_missing"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_revision_cannot_self_parent() -> None:
    bad = candidate("c2", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="c2")
    with pytest.raises(DebateContractError, match="candidate_self_parent"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_revision_must_be_sequential() -> None:
    root = candidate("c1")
    bad = candidate("c3", revision=3, status=CandidateStatus.REVISED, parent_candidate_id="c1")
    with pytest.raises(DebateContractError, match="candidate_revision_not_sequential"):
        DebateRound("round-1", "task-1", SUBJECT, (root, bad)).validate()


def test_lineage_cycle_is_rejected_before_revision_arithmetic() -> None:
    c1 = candidate("c1", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="c3")
    c2 = candidate("c2", revision=3, status=CandidateStatus.REVISED, parent_candidate_id="c1")
    c3 = candidate("c3", revision=4, status=CandidateStatus.REVISED, parent_candidate_id="c2")
    with pytest.raises(DebateContractError, match="candidate_lineage_cycle"):
        DebateRound("round-1", "task-1", SUBJECT, (c1, c2, c3)).validate()


def test_ambiguous_direct_revision_branch_is_rejected() -> None:
    root = candidate("c1")
    c2a = candidate("c2a", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="c1")
    c2b = candidate("c2b", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="c1")
    with pytest.raises(DebateContractError, match="candidate_lineage_ambiguous"):
        DebateRound("round-1", "task-1", SUBJECT, (root, c2a, c2b)).validate()


def test_valid_revision_chain_is_accepted_and_deterministic() -> None:
    c1 = candidate("c1")
    c2 = candidate("c2", revision=2, status=CandidateStatus.REVISED, parent_candidate_id="c1")
    c3 = candidate("c3", revision=3, status=CandidateStatus.REVISED, parent_candidate_id="c2")
    left = DebateRound("round-1", "task-1", SUBJECT, (c1, c2, c3))
    right = DebateRound("round-1", "task-1", SUBJECT, (c3, c1, c2))
    left.validate()
    right.validate()
    assert left.canonical_digest() == right.canonical_digest()


def test_measured_candidate_requires_evidence() -> None:
    bad = candidate(status=CandidateStatus.MEASURED_NOT_VERIFIED)
    with pytest.raises(DebateContractError, match="measured_candidate_evidence_required"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_verified_state_does_not_exist() -> None:
    with pytest.raises(ValueError):
        CandidateStatus("VERIFIED")


def test_measured_candidate_with_evidence_is_valid_but_not_verified() -> None:
    measured = candidate(
        status=CandidateStatus.MEASURED_NOT_VERIFIED,
        evidence_refs=("evidence:sha256:abc",),
    )
    round_ = DebateRound("round-1", "task-1", SUBJECT, (measured,))
    round_.validate()
    assert round_.verification_ceiling == "MEASURED_NOT_VERIFIED"


def test_raw_status_string_cannot_bypass_verification_ceiling() -> None:
    bad = candidate(status="VERIFIED")
    with pytest.raises(DebateContractError, match="candidate_status_invalid"):
        DebateRound("round-1", "task-1", SUBJECT, (bad,)).validate()


def test_raw_critique_severity_is_rejected() -> None:
    bad = critique(severity="BLOCKING")
    with pytest.raises(DebateContractError, match="critique_severity_invalid"):
        DebateRound("round-1", "task-1", SUBJECT, (candidate(),), (bad,)).validate()
