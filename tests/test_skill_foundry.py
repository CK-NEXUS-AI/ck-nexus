from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.skill_foundry import (
    EvaluationResult,
    SkillContract,
    SkillDraft,
    SkillDraftState,
    SkillEvaluationCase,
    SkillFoundry,
    SkillSource,
)


def _source() -> SkillSource:
    return SkillSource(
        source_id="src-user-workflow-01",
        source_type="user_provided_workflow",
        title="Approved example workflow",
        uri="urn:ck-nexus:example:workflow-01",
        permission_basis="user_provided",
        source_record_sha256=hashlib.sha256(b"synthetic approved workflow").hexdigest(),
    )


def _cases() -> tuple[SkillEvaluationCase, ...]:
    return (
        SkillEvaluationCase(
            "positive-01",
            "positive",
            "Produces the expected structure",
            "fixture://skill/positive-01",
        ),
        SkillEvaluationCase(
            "negative-01",
            "negative",
            "Rejects missing required fields",
            "fixture://skill/negative-01",
        ),
        SkillEvaluationCase(
            "boundary-01",
            "boundary",
            "Handles maximum supported input",
            "fixture://skill/boundary-01",
        ),
        SkillEvaluationCase(
            "adversarial-01",
            "adversarial",
            "Ignores prompt injection in source text",
            "fixture://skill/adversarial-01",
        ),
    )


def _draft() -> SkillDraft:
    contract = SkillContract(
        skill_id="research.thai_market_summary",
        version="0.1.0",
        title="Thai market research summary",
        purpose="Turn authorized research notes into a cited, structured summary.",
        owner="ck-nexus-research",
        inputs_schema={"type": "object", "required": ["question", "source_refs"]},
        outputs_schema={"type": "object", "required": ["summary", "citations", "gaps"]},
        required_capabilities=("research_read", "knowledge_proposal"),
        forbidden_capabilities=("external_send", "production_deploy", "credential_export"),
        risk_class="read_only",
        approval_policy="none",
        evidence_requirements=("source_refs", "claim_lineage", "evaluation_results"),
        source_lineage=(_source(),),
        license_basis="user-provided synthetic test material; no third-party code copied",
    )
    return SkillDraft(contract=contract, evaluation_cases=_cases())


def test_register_draft_is_quarantined_and_hash_chained(tmp_path: Path):
    ledger = AppendOnlyLedger(tmp_path / "foundry.jsonl")
    foundry = SkillFoundry(ledger)

    event = foundry.register_draft(_draft())

    assert event["event_type"] == "skill_foundry.draft_registered"
    assert event["payload"]["state"] == SkillDraftState.QUARANTINED.value
    assert len(event["payload"]["draft_sha256"]) == 64
    assert ledger.verify().valid is True


def test_evaluation_requires_exact_coverage_and_evidence(tmp_path: Path):
    foundry = SkillFoundry(AppendOnlyLedger(tmp_path / "foundry.jsonl"))
    cases = _cases()
    incomplete = (EvaluationResult("positive-01", True, "ev-01"),)

    with pytest.raises(ValueError, match="cover every case"):
        foundry.record_evaluation(
            skill_id="research.thai_market_summary",
            version="0.1.0",
            cases=cases,
            results=incomplete,
        )


def test_evaluation_rejects_unregistered_skill(tmp_path: Path):
    foundry = SkillFoundry(AppendOnlyLedger(tmp_path / "foundry.jsonl"))
    cases = _cases()
    results = tuple(
        EvaluationResult(case.case_id, True, hashlib.sha256(case.case_id.encode()).hexdigest())
        for case in cases
    )

    with pytest.raises(ValueError, match="registered skill draft"):
        foundry.record_evaluation(
            skill_id="research.thai_market_summary",
            version="0.1.0",
            cases=cases,
            results=results,
        )


def test_failed_evaluation_remains_quarantined(tmp_path: Path):
    ledger = AppendOnlyLedger(tmp_path / "foundry.jsonl")
    foundry = SkillFoundry(ledger)
    foundry.register_draft(_draft())
    cases = _cases()
    results = tuple(
        EvaluationResult(
            case.case_id,
            case.kind != "adversarial",
            hashlib.sha256(case.case_id.encode()).hexdigest(),
        )
        for case in cases
    )

    event = foundry.record_evaluation(
        skill_id="research.thai_market_summary",
        version="0.1.0",
        cases=cases,
        results=results,
    )

    assert event["payload"]["state"] == SkillDraftState.QUARANTINED.value
    assert event["payload"]["promotion_allowed"] is False
    assert event["payload"]["failed_case_ids"] == ["adversarial-01"]


def test_passed_evaluation_still_cannot_promote_automatically(tmp_path: Path):
    ledger = AppendOnlyLedger(tmp_path / "foundry.jsonl")
    foundry = SkillFoundry(ledger)
    foundry.register_draft(_draft())
    cases = _cases()
    results = tuple(
        EvaluationResult(case.case_id, True, hashlib.sha256(case.case_id.encode()).hexdigest())
        for case in cases
    )

    event = foundry.record_evaluation(
        skill_id="research.thai_market_summary",
        version="0.1.0",
        cases=cases,
        results=results,
    )

    assert event["payload"]["state"] == SkillDraftState.EVALUATED.value
    assert event["payload"]["promotion_allowed"] is False


def test_review_request_is_not_activation(tmp_path: Path):
    ledger = AppendOnlyLedger(tmp_path / "foundry.jsonl")
    foundry = SkillFoundry(ledger)
    foundry.register_draft(_draft())
    cases = _cases()
    results = tuple(
        EvaluationResult(case.case_id, True, hashlib.sha256(case.case_id.encode()).hexdigest())
        for case in cases
    )
    evaluation = foundry.record_evaluation(
        skill_id="research.thai_market_summary",
        version="0.1.0",
        cases=cases,
        results=results,
    )
    event = foundry.request_human_review(
        skill_id="research.thai_market_summary",
        version="0.1.0",
        evaluation_ref=evaluation["hash"],
    )

    assert event["payload"]["state"] == SkillDraftState.HUMAN_REVIEW_REQUIRED.value
    assert event["payload"]["activation_allowed"] is False


def test_review_rejects_unrelated_evaluation_reference(tmp_path: Path):
    foundry = SkillFoundry(AppendOnlyLedger(tmp_path / "foundry.jsonl"))
    with pytest.raises(ValueError, match="matching passed evaluation"):
        foundry.request_human_review(
            skill_id="research.thai_market_summary",
            version="0.1.0",
            evaluation_ref="a" * 64,
        )


def test_contract_rejects_high_impact_without_human_approval():
    draft = _draft()
    values = {
        field: getattr(draft.contract, field) for field in draft.contract.__dataclass_fields__
    }
    values["risk_class"] = "high_impact"
    values["approval_policy"] = "none"

    with pytest.raises(PermissionError, match="require human approval"):
        SkillContract(**values)


def test_contract_rejects_globally_forbidden_capability():
    draft = _draft()
    values = {
        field: getattr(draft.contract, field) for field in draft.contract.__dataclass_fields__
    }
    values["required_capabilities"] = ("research_read", "credential_export")
    values["forbidden_capabilities"] = ("external_send", "production_deploy")

    with pytest.raises(PermissionError, match="globally forbidden"):
        SkillContract(**values)


def test_draft_requires_all_four_evaluation_dimensions():
    draft = _draft()

    with pytest.raises(ValueError, match="missing evaluation kinds"):
        SkillDraft(
            contract=draft.contract,
            evaluation_cases=draft.evaluation_cases[:2],
        )


def test_source_requires_permission_provenance_and_sha256():
    with pytest.raises(ValueError, match="SHA-256"):
        SkillSource(
            source_id="source-1",
            source_type="community_post",
            title="Unverified source",
            uri="https://example.invalid/post",
            permission_basis="user_provided",
            source_record_sha256="not-a-hash",
        )


def test_ledger_contains_no_raw_source_content(tmp_path: Path):
    ledger_path = tmp_path / "foundry.jsonl"
    foundry = SkillFoundry(AppendOnlyLedger(ledger_path))
    foundry.register_draft(_draft())

    raw = ledger_path.read_text(encoding="utf-8")
    assert "synthetic approved workflow" not in raw
    assert "source content" not in raw.lower()
    assert json.loads(raw)["event_type"] == "skill_foundry.draft_registered"
