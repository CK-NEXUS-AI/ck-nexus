from __future__ import annotations

from creator_app.global_knowledge.connectors.searxng import SearchHit
from scripts.research_stack_e2e import (
    compile_discovery,
    lineage_id_for_source,
    source_from_hit,
)


def hit(url: str, title: str = "Example") -> SearchHit:
    return SearchHit(
        url=url,
        title=title,
        snippet="discovery snippet",
        engine="test",
    )


def test_discovered_source_identity_is_stable_and_unverified() -> None:
    first = source_from_hit(
        hit("https://example.test/a"),
        observed_at="2026-09-07T00:00:00+00:00",
    )
    second = source_from_hit(
        hit("https://example.test/a"),
        observed_at="2026-09-07T00:01:00+00:00",
    )

    assert first.source_id == second.source_id
    assert first.content_hash == second.content_hash
    assert first.metadata["discovery_only"] is True


def test_lineage_groups_sources_by_hostname() -> None:
    a = source_from_hit(
        hit("https://example.test/a"),
        observed_at="2026-09-07T00:00:00+00:00",
    )
    b = source_from_hit(
        hit("https://example.test/b"),
        observed_at="2026-09-07T00:00:00+00:00",
    )

    assert lineage_id_for_source(a) == lineage_id_for_source(b)


def test_discovery_compilation_never_creates_claims_or_verification() -> None:
    hits = (
        hit("https://one.example/a"),
        hit("https://two.example/b"),
        hit("https://three.example/c"),
    )
    sources, artifact, decision = compile_discovery(
        hits,
        observed_at="2026-09-07T00:00:00+00:00",
    )

    assert len(sources) == 3
    assert artifact.claim_ids == ()
    assert artifact.verified is False
    assert artifact.ready_for_analysis is True
    assert decision.action.name == "READY_FOR_ANALYSIS"
