from __future__ import annotations

import pytest

from creator_app.verifier_pro.gap_analysis import GapStatus, SubjectGapAnalyzer
from creator_app.verifier_pro.subject import (
    SubjectComponent,
    SubjectValidationError,
    VerificationSubject,
    canonical_sha256,
    fingerprint_public_environment,
)


def _subject(**overrides: str | None) -> VerificationSubject:
    values: dict[str, str | None] = {
        "repository": "spinlnw10-art/ck-nexus",
        "repository_sha": "a" * 40,
        "tree_sha": "b" * 40,
        "environment_digest": "c" * 64,
        "plan_digest": "d" * 64,
        "dependency_digest": "e" * 64,
        "policy_digest": "f" * 64,
        "toolchain_digest": "1" * 64,
        "archive_digest": "2" * 64,
    }
    values.update(overrides)
    return VerificationSubject(**values)  # type: ignore[arg-type]


def test_subject_id_is_deterministic_and_full_digest_is_authoritative() -> None:
    first = _subject()
    second = _subject()

    assert first.digest == second.digest
    assert first.subject_id == second.subject_id
    assert first.subject_id == f"VFY-{first.digest[:16].upper()}"
    assert len(first.digest) == 64


def test_canonical_digest_is_key_order_independent() -> None:
    left = canonical_sha256({"runtime": "python3.12", "arch": "x86_64"})
    right = canonical_sha256({"arch": "x86_64", "runtime": "python3.12"})
    assert left == right


def test_environment_fingerprint_rejects_secret_like_keys() -> None:
    with pytest.raises(SubjectValidationError, match="secret-like"):
        fingerprint_public_environment({"runtime": "python3.12", "api_key": "do-not-hash"})


def test_changed_subject_cannot_rebind_old_evidence() -> None:
    previous = _subject()
    current = _subject(tree_sha="3" * 40)

    decision = SubjectGapAnalyzer().assess(
        current=current,
        previous=previous,
        ledger_valid=True,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert decision.status is GapStatus.SUBJECT_CHANGED
    assert SubjectComponent.TREE in decision.changed_components
    assert decision.authoritative_reuse_allowed is False
    assert decision.historical_reference_allowed is True
    assert decision.rerun_scopes


def test_any_plan_change_creates_new_subject_and_requires_regeneration() -> None:
    previous = _subject()
    current = _subject(plan_digest="4" * 64)

    decision = SubjectGapAnalyzer().assess(
        current=current,
        previous=previous,
        ledger_valid=True,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert decision.status is GapStatus.SUBJECT_CHANGED
    assert decision.changed_components == (SubjectComponent.PLAN,)
    assert decision.authoritative_reuse_allowed is False


def test_invalid_ledger_blocks_even_exact_subject() -> None:
    subject = _subject()
    decision = SubjectGapAnalyzer().assess(
        current=subject,
        previous=subject,
        ledger_valid=False,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert decision.status is GapStatus.BLOCK_INVALID_LEDGER
    assert decision.authoritative_reuse_allowed is False


def test_invalid_verifier_separation_blocks_reuse() -> None:
    subject = _subject()
    decision = SubjectGapAnalyzer().assess(
        current=subject,
        previous=subject,
        ledger_valid=True,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=False,
    )

    assert decision.status is GapStatus.BLOCK_VERIFIER_SEPARATION
    assert decision.authoritative_reuse_allowed is False


def test_stale_evidence_requires_rerun() -> None:
    subject = _subject()
    decision = SubjectGapAnalyzer().assess(
        current=subject,
        previous=subject,
        ledger_valid=True,
        evidence_complete=True,
        evidence_fresh=False,
        verifier_separation_valid=True,
    )

    assert decision.status is GapStatus.RERUN_STALE_EVIDENCE
    assert decision.authoritative_reuse_allowed is False


def test_exact_subject_reuse_requires_all_guards() -> None:
    subject = _subject()
    decision = SubjectGapAnalyzer().assess(
        current=subject,
        previous=subject,
        ledger_valid=True,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert decision.status is GapStatus.REUSE_EXACT_SUBJECT
    assert decision.authoritative_reuse_allowed is True
    assert decision.rerun_scopes == ()
