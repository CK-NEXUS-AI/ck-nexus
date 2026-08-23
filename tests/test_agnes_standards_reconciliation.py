from creator_app.agnes.knowledge_repository import (
    AdoptionMode,
    KnowledgeCatalog,
    KnowledgeItem,
    KnowledgeStatus,
    predevelopment_search,
    standards_catalog,
)


def _item(*, mode: AdoptionMode) -> KnowledgeItem:
    return KnowledgeItem(
        item_id=f"test.{mode.value}",
        name=f"Test {mode.value}",
        category="test",
        summary="candidate capability",
        usage="test only",
        status=KnowledgeStatus.ADOPTABLE,
        sources=(),
        adoption_mode=mode,
        capabilities=("candidate_capability",),
    )


def test_study_only_entry_does_not_block_new_work() -> None:
    catalog = KnowledgeCatalog((_item(mode=AdoptionMode.STUDY),))
    decision = predevelopment_search(catalog, "candidate capability")

    assert decision.matches
    assert decision.build_new_allowed is True


def test_adopt_entry_blocks_duplicate_build() -> None:
    catalog = KnowledgeCatalog((_item(mode=AdoptionMode.ADOPT),))
    decision = predevelopment_search(catalog, "candidate capability")

    assert decision.matches
    assert decision.build_new_allowed is False


def test_wrap_entry_blocks_duplicate_build() -> None:
    catalog = KnowledgeCatalog((_item(mode=AdoptionMode.WRAP),))
    decision = predevelopment_search(catalog, "candidate capability")

    assert decision.matches
    assert decision.build_new_allowed is False


def test_current_mcp_baseline_is_2026_07_28() -> None:
    item = standards_catalog().get("standard.mcp.2026_07_28")

    assert item is not None
    assert item.adoption_mode is AdoptionMode.ADOPT
    assert "stateless_protocol" in item.capabilities
    assert any("2025-06-18" in note and "stale" in note for note in item.observations)


def test_a2a_is_pinned_to_v1() -> None:
    item = standards_catalog().get("standard.a2a.v1_0")

    assert item is not None
    assert "version_negotiation" in item.capabilities
    assert "signed_agent_cards" in item.capabilities


def test_opentelemetry_tracks_genai_conventions_separately() -> None:
    item = standards_catalog().get("standard.opentelemetry.semconv.1_44")

    assert item is not None
    joined = " ".join(item.observations)
    assert "GenAI" in joined
    assert "deprecated" in joined


def test_management_guidance_does_not_block_new_runtime_work() -> None:
    catalog = standards_catalog()

    nist = catalog.get("standard.nist.ai_rmf_genai")
    iso = catalog.get("standard.iso.iec.42001")
    assert nist is not None and nist.adoption_mode is AdoptionMode.STUDY
    assert iso is not None and iso.adoption_mode is AdoptionMode.STUDY

    decision = predevelopment_search(catalog, "AI management governance")
    assert decision.build_new_allowed is True


def test_openai_agents_sdk_is_wrapped_not_made_authority() -> None:
    item = standards_catalog().get("reference.openai.agents_sdk")

    assert item is not None
    assert item.adoption_mode is AdoptionMode.WRAP
    assert any("do not self-approve" in note.lower() for note in item.observations)
