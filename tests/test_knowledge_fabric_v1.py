from datetime import UTC, datetime

import pytest

from idea_engine.knowledge_fabric import (
    ClaimClass,
    KnowledgeClaim,
    KnowledgeFabric,
    SourceClass,
    SourceRecord,
    VerificationState,
    freshness_score,
)


def source(source_id: str, value: float = 0.9) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_class=SourceClass.RESEARCH,
        locator=f"https://example.test/{source_id}",
        title=source_id,
        retrieved_at="2026-09-03T00:00:00Z",
        trust_score=value,
        language="en",
    )


def claim(
    claim_id: str,
    value: str,
    *,
    source_id: str = "s1",
    claim_class: ClaimClass = ClaimClass.FACT,
) -> KnowledgeClaim:
    return KnowledgeClaim(
        claim_id=claim_id,
        subject="CK-NEXUS",
        predicate="runtime-state",
        value=value,
        claim_class=claim_class,
        source_ids=(source_id,),
        confidence=0.8,
        observed_at="2026-09-03T00:00:00Z",
        verification=VerificationState.OBSERVED,
    )


def test_source_rejects_invalid_trust_score() -> None:
    with pytest.raises(ValueError, match="trust_score"):
        source("bad", 1.1)


def test_claim_requires_known_provenance() -> None:
    fabric = KnowledgeFabric()
    with pytest.raises(ValueError, match="unknown source_ids"):
        fabric.add_claim(claim("c1", "working"))


def test_synthesis_keeps_fact_inference_and_prediction_separate() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_claim(claim("fact", "working"))
    fabric.add_claim(claim("inference", "likely scalable", claim_class=ClaimClass.INFERENCE))
    fabric.add_claim(claim("prediction", "future growth", claim_class=ClaimClass.PREDICTION))

    view = fabric.synthesis_view()

    assert [item.claim_id for item in view.facts] == ["fact"]
    assert [item.claim_id for item in view.inferences] == ["inference"]
    assert [item.claim_id for item in view.predictions] == ["prediction"]


def test_conflict_detection_preserves_both_claims() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_source(source("s2"))
    fabric.add_claim(claim("c1", "working", source_id="s1"))
    fabric.add_claim(claim("c2", "blocked", source_id="s2"))

    conflicts = fabric.conflict_groups()

    assert len(conflicts) == 1
    assert conflicts[0].claim_ids == ("c1", "c2")
    assert set(conflicts[0].values) == {"working", "blocked"}


def test_freshness_and_source_weight_decay_with_age() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1", 1.0))
    item = fabric.add_claim(claim("c1", "working"))
    now = datetime(2026, 10, 3, tzinfo=UTC)

    assert freshness_score("2026-09-03T00:00:00Z", now=now) == pytest.approx(0.5)
    assert fabric.source_weight(item, now=now) == pytest.approx(0.4)


def test_memory_write_is_proposal_not_self_approval() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_claim(claim("c1", "working"))

    proposal = fabric.propose_memory_write(
        content="Docker core runtime was observed working.",
        source_claim_ids=("c1",),
        scope="episodic",
        retention_days=30,
    )

    assert proposal.consent_required is True
    assert proposal.auto_approved is False


def test_memory_write_cannot_mutate_protected_authority_scope() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_claim(claim("c1", "working"))

    with pytest.raises(PermissionError, match="protected authority"):
        fabric.propose_memory_write(
            content="Mark system verified.",
            source_claim_ids=("c1",),
            scope="release_gate",
            retention_days=30,
        )


def test_claim_maps_into_existing_idea_graph_model() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_claim(claim("c1", "working"))

    node = fabric.claim_to_idea_node("c1")

    assert node.id == "knowledge:c1"
    assert node.type == "evidence"
    assert node.source_refs == ["s1"]
    assert "knowledge-fabric" in node.tags
