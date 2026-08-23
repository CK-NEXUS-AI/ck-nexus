from datetime import UTC, datetime

import pytest

from creator_app.agnes.knowledge_repository import (
    AdoptionMode,
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
    universal_control_catalog,
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


def test_market_snapshot_rejects_stale_langgraph_positioning() -> None:
    item = initial_catalog().get("market.langgraph.2026")

    assert item is not None
    assert "checkpointing" in item.capabilities
    assert "human_in_the_loop" in item.capabilities
    assert any("Do not claim" in observation for observation in item.observations)


def test_market_snapshot_tracks_current_microsoft_framework() -> None:
    item = initial_catalog().get("market.microsoft.agent_framework.2026")

    assert item is not None
    assert "graph_workflow" in item.capabilities
    assert "checkpointing" in item.capabilities
    assert "AutoGen" in item.relevance
    assert "Semantic Kernel" in item.relevance


def test_gateway_market_snapshot_records_modern_governance() -> None:
    catalog = initial_catalog()

    portkey = catalog.get("market.portkey.2026")
    openrouter = catalog.get("market.openrouter.2026")
    aws = catalog.get("market.aws.agentcore.2026")

    assert portkey is not None and "rbac" in portkey.capabilities
    assert openrouter is not None and "zdr" in openrouter.capabilities
    assert aws is not None and "deny_by_default" in aws.capabilities


def test_thai_market_snapshot_treats_typhoon_as_reusable_provider() -> None:
    item = initial_catalog().get("market.typhoon.2026")

    assert item is not None
    assert item.status is KnowledgeStatus.ADOPTABLE
    assert "thai_language" in item.capabilities
    assert "function_calling" in item.capabilities


def test_assurance_market_wedge_is_explicitly_an_inference() -> None:
    item = initial_catalog().get("market.assurance.wedge.2026")

    assert item is not None
    assert "evidence_by_construction" in item.capabilities
    assert "independent_verification" in item.capabilities
    assert any("market inference" in observation for observation in item.observations)


def test_universal_control_catalog_has_broad_multi_system_coverage() -> None:
    catalog = universal_control_catalog()
    items = catalog.all()

    assert len(items) >= 30
    assert len({item.item_id for item in items}) == len(items)
    categories = {item.category for item in items}
    assert {
        "durable_runtime",
        "workflow_orchestration",
        "policy_authorization",
        "identity",
        "interoperability_protocol",
        "connector_fabric",
        "observability_evaluation",
        "memory_context",
        "sandbox_execution",
        "browser_execution",
        "local_inference",
    }.issubset(categories)


def test_universal_control_catalog_uses_documented_sources_only() -> None:
    for item in universal_control_catalog().all():
        assert item.status is KnowledgeStatus.ADOPTABLE
        assert item.status is not KnowledgeStatus.ADOPTED
        assert item.sources
        for source in item.sources:
            assert source.evidence_level is EvidenceLevel.DOCUMENTED
            assert source.url.startswith("https://")


def test_universal_control_fabric_marks_core_spine_for_adoption() -> None:
    catalog = universal_control_catalog()

    expected = {
        "control.runtime.dapr_agents",
        "control.policy.opa",
        "control.authorization.openfga",
        "control.identity.spiffe_spire",
        "control.protocol.mcp",
        "control.protocol.a2a",
        "control.protocol.agui",
        "control.memory.graphiti",
        "control.inference.ollama",
        "control.inference.vllm",
    }
    for item_id in expected:
        item = catalog.get(item_id)
        assert item is not None
        assert item.adoption_mode is AdoptionMode.ADOPT


def test_external_systems_never_gain_ck_authority_by_catalog_presence() -> None:
    catalog = universal_control_catalog()

    dapr = catalog.get("control.runtime.dapr_agents")
    graphiti = catalog.get("control.memory.graphiti")
    browser = catalog.get("control.browser.browserbase")

    assert dapr is not None
    assert any("not production authority" in note for note in dapr.observations)
    assert graphiti is not None
    assert any("canonical history" in note for note in graphiti.observations)
    assert browser is not None
    assert any("must not" in note for note in browser.observations)


def test_browser_automation_remains_bounded_by_access_governance() -> None:
    item = universal_control_catalog().get("control.browser.browserbase")

    assert item is not None
    assert item.adoption_mode is AdoptionMode.WRAP
    joined = " ".join(item.observations).casefold()
    assert "captcha" in joined
    assert "authorization" in joined


def test_dapr_research_prevents_stale_evidence_uniqueness_claim() -> None:
    item = universal_control_catalog().get("control.runtime.dapr_agents")

    assert item is not None
    assert "durable_execution" in item.capabilities
    assert any("must not claim" in note for note in item.observations)
