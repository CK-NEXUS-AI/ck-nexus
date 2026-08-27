from __future__ import annotations

import json
from pathlib import Path

import pytest

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.verifier_pro.gap_analysis import GapStatus
from creator_app.verifier_pro.shadow_controller import VerifierShadowController
from creator_app.verifier_pro.subject import VerificationSubject


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


def test_shadow_controller_records_exact_subject_reuse(tmp_path: Path) -> None:
    ledger = AppendOnlyLedger(tmp_path / "verifier.jsonl")
    subject = _subject()

    observation = VerifierShadowController(ledger).observe(
        current=subject,
        previous=subject,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert observation.decision.status is GapStatus.REUSE_EXACT_SUBJECT
    assert observation.ledger_sequence == 1
    state = ledger.verify()
    assert state.valid is True
    assert state.entries == 1
    assert state.last_hash == observation.record_hash

    record = json.loads((tmp_path / "verifier.jsonl").read_text(encoding="utf-8"))
    assert record["event_type"] == "VERIFIER_SUBJECT_GAP_DECISION"
    assert record["payload"]["subject_digest"] == subject.digest
    assert record["payload"]["authoritative_reuse_allowed"] is True
    assert record["payload"]["production_mutation"] is False
    assert record["payload"]["verification_authority"] is False


def test_subject_change_is_recorded_without_rebinding_old_evidence(tmp_path: Path) -> None:
    ledger = AppendOnlyLedger(tmp_path / "verifier.jsonl")
    previous = _subject()
    current = _subject(tree_sha="3" * 40)

    observation = VerifierShadowController(ledger).observe(
        current=current,
        previous=previous,
        evidence_complete=True,
        evidence_fresh=True,
        verifier_separation_valid=True,
    )

    assert observation.decision.status is GapStatus.SUBJECT_CHANGED
    assert observation.decision.authoritative_reuse_allowed is False

    record = json.loads((tmp_path / "verifier.jsonl").read_text(encoding="utf-8"))
    assert record["payload"]["subject_digest"] == current.digest
    assert record["payload"]["previous_subject_digest"] == previous.digest
    assert record["payload"]["authoritative_reuse_allowed"] is False


def test_controller_refuses_to_append_when_ledger_is_tampered(tmp_path: Path) -> None:
    path = tmp_path / "verifier.jsonl"
    ledger = AppendOnlyLedger(path)
    ledger.append("BASELINE", {"value": 1})

    record = json.loads(path.read_text(encoding="utf-8"))
    record["payload"]["value"] = 2
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    subject = _subject()
    with pytest.raises(RuntimeError, match="invalid evidence ledger"):
        VerifierShadowController(ledger).observe(
            current=subject,
            previous=subject,
            evidence_complete=True,
            evidence_fresh=True,
            verifier_separation_valid=True,
        )

    assert ledger.verify().valid is False


def test_new_subject_record_has_no_previous_identity(tmp_path: Path) -> None:
    ledger = AppendOnlyLedger(tmp_path / "verifier.jsonl")
    subject = _subject()

    observation = VerifierShadowController(ledger).observe(
        current=subject,
        previous=None,
        evidence_complete=False,
        evidence_fresh=False,
        verifier_separation_valid=False,
    )

    assert observation.decision.status is GapStatus.NEW_SUBJECT
    record = json.loads((tmp_path / "verifier.jsonl").read_text(encoding="utf-8"))
    assert record["payload"]["previous_subject_id"] is None
    assert record["payload"]["previous_subject_digest"] is None
    assert record["payload"]["authoritative_reuse_allowed"] is False
