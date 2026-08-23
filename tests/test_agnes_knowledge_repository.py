from datetime import UTC, datetime

import pytest

from creator_app.agnes.knowledge_repository import (
    AttemptRecord,
    EvidenceLevel,
    KnowledgeSource,
    KnowledgeStatus,
    best_capability_matches,
    collect_unknown,
    enforce_two_strike,
    initial_catalog,
    predevelopment_search,
    transition_status,
)


def test_predevelopment_search_blocks_duplicate_build_when_reusable_exists() -> None:
    decision = predevelopment_search(initial_catalog(), "long term memory")
    assert decision.matches
    assert decision.build_new_allowed is False


def test_capability_matcher_prefers_recorded_capabilities() -> None:
    matches = best_capability_matches(
        initial_catalog(),
        {"text_to_speech", "offline_voice"},
    )
    assert matches
    assert matches[0].item_id == "voice.piper"


def test_two_strike_policy_stops_after_second_failed_attempt() -> None:
    assert enforce_two_strike(AttemptRecord("problem", 0)) == "continue_bounded_attempt"
    assert enforce_two_strike(AttemptRecord("problem", 1)) == "continue_bounded_attempt"
    assert enforce_two_strike(AttemptRecord("problem", 2)) == "stop_and_research"


def test_unknown_item_starts_pending_and_uses_explicit_transitions() -> None:
    source = KnowledgeSource(
        source_id="source.test",
        name="Source",
        url="https://example.com/source",
        source_type="official_docs",
        discovered_at=datetime(2026, 8, 23, tzinfo=UTC),
        evidence_level=EvidenceLevel.DOCUMENTED,
    )
    item = collect_unknown(
        item_id="unknown.test",
        name="Unknown capability",
        category="test",
        summary="Newly discovered capability.",
        usage="Study before adoption.",
        source=source,
    )
    assert item.status is KnowledgeStatus.PENDING_REVIEW

    studying = transition_status(item, KnowledgeStatus.STUDYING)
    understood = transition_status(studying, KnowledgeStatus.UNDERSTOOD)
    adoptable = transition_status(understood, KnowledgeStatus.ADOPTABLE)
    assert adoptable.status is KnowledgeStatus.ADOPTABLE

    with pytest.raises(ValueError):
        transition_status(item, KnowledgeStatus.ADOPTED)
