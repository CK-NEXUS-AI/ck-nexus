from __future__ import annotations

import json

import pytest

from creator_app.council_debate import (
    DebateContribution,
    DebatePolicy,
    DebateRole,
    DebateStance,
    DebateStatus,
    build_final_vote_prompt,
    build_mock_debate_report,
    moderate_votes,
    parse_contribution,
)


def contribution(
    role: DebateRole,
    stance: DebateStance,
    summary: str,
    *,
    evidence_refs: tuple[str, ...] = ("evidence:x",),
    safety_concern: bool = False,
) -> DebateContribution:
    return DebateContribution(
        role=role,
        stance=stance,
        confidence=0.8,
        summary=summary,
        evidence_refs=evidence_refs,
        safety_concern=safety_concern,
    )


def test_parse_contribution_accepts_structured_json() -> None:
    raw = json.dumps(
        {
            "stance": "SUPPORT",
            "confidence": 0.8,
            "summary": "Use the existing Council.",
            "evidence_refs": ["repo:creator_app/dev_team.py"],
            "claims": ["Council exists"],
            "risks": [],
            "questions": [],
            "safety_concern": False,
        }
    )

    parsed, violations = parse_contribution(raw, role=DebateRole.PROPOSER)

    assert parsed.stance is DebateStance.SUPPORT
    assert parsed.evidence_refs == ("repo:creator_app/dev_team.py",)
    assert violations == ()


def test_word_limit_is_deterministically_flagged() -> None:
    policy = DebatePolicy(max_words_per_turn=50)
    raw = json.dumps(
        {
            "stance": "UNCERTAIN",
            "confidence": 0.5,
            "summary": "word " * 51,
            "evidence_refs": [],
            "claims": [],
            "risks": [],
            "questions": [],
            "safety_concern": False,
        }
    )

    _parsed, violations = parse_contribution(
        raw,
        role=DebateRole.EXAMINER,
        policy=policy,
    )

    assert violations == ("EXAMINER:word_limit_exceeded:51>50",)


def test_three_support_votes_reach_advisory_consensus() -> None:
    votes = (
        contribution(DebateRole.PROPOSER, DebateStance.SUPPORT, "proposal accepted"),
        contribution(DebateRole.OPPOSER, DebateStance.SUPPORT, "critique resolved"),
        contribution(DebateRole.EXAMINER, DebateStance.SUPPORT, "evidence adequate"),
    )

    result = moderate_votes(votes)

    assert result.status is DebateStatus.CONSENSUS_REACHED
    assert result.consensus_score == 1.0
    assert result.authority_effect == "NONE"


def test_uncertainty_requests_more_evidence() -> None:
    votes = (
        contribution(DebateRole.PROPOSER, DebateStance.SUPPORT, "support"),
        contribution(DebateRole.OPPOSER, DebateStance.OPPOSE, "oppose"),
        contribution(
            DebateRole.EXAMINER,
            DebateStance.UNCERTAIN,
            "needs evidence",
            evidence_refs=(),
        ),
    )

    result = moderate_votes(votes)

    assert result.status is DebateStatus.MORE_EVIDENCE_REQUIRED


def test_material_safety_concern_escalates_to_human_review() -> None:
    votes = (
        contribution(DebateRole.PROPOSER, DebateStance.SUPPORT, "support"),
        contribution(
            DebateRole.OPPOSER,
            DebateStance.OPPOSE,
            "unsafe production path",
            safety_concern=True,
        ),
        contribution(DebateRole.EXAMINER, DebateStance.SUPPORT, "supported"),
    )

    result = moderate_votes(votes)

    assert result.status is DebateStatus.HUMAN_REVIEW_REQUIRED


def test_duplicate_final_turns_fail_closed() -> None:
    votes = (
        contribution(DebateRole.PROPOSER, DebateStance.SUPPORT, "same"),
        contribution(DebateRole.OPPOSER, DebateStance.SUPPORT, "same"),
        contribution(DebateRole.EXAMINER, DebateStance.SUPPORT, "different"),
    )

    result = moderate_votes(votes)

    assert result.status is DebateStatus.HUMAN_REVIEW_REQUIRED
    assert any("duplicate_turn" in item for item in result.rule_violations)


def test_final_vote_prompt_rejects_synthesizer_role() -> None:
    synthesis = contribution(
        DebateRole.SYNTHESIZER,
        DebateStance.SYNTHESIS,
        "draft resolution",
    )

    with pytest.raises(ValueError):
        build_final_vote_prompt(
            DebateRole.SYNTHESIZER,
            objective="test",
            synthesis=synthesis,
            language="English",
        )


def test_mock_report_never_claims_verified_authority() -> None:
    report = build_mock_debate_report("Design the next CK-NEXUS debate capability")

    assert "CONSENSUS_REACHED" in report
    assert "authority_effect: NONE" in report
    assert "not independent human review" in report
    assert "Production authorization" in report
