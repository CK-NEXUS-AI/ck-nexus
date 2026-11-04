from datetime import UTC, datetime

import pytest

from idea_engine.knowledge_fabric import (
    ClaimClass,
    KnowledgeClaim,
    KnowledgeFabric,
    RetentionClass,
    SourceClass,
    SourceRecord,
    VerificationState,
    freshness_score,
)


def source(
    source_id: str,
    value: float = 0.9,
    *,
    tenant_id: str = "default",
    source_hash: str | None = None,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_class=SourceClass.RESEARCH,
        locator=f"https://example.test/{source_id}",
        title=source_id,
        retrieved_at="2026-09-03T00:00:00Z",
        trust_score=value,
        tenant_id=tenant_id,
        source_hash=source_hash,
        language="en",
    )


def claim(
    claim_id: str,
    value: str,
    *,
    source_id: str = "s1",
    claim_class: ClaimClass = ClaimClass.FACT,
    tenant_id: str = "default",
    fresh_until: str | None = None,
    contradicts: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
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
        tenant_id=tenant_id,
        verification=VerificationState.OBSERVED,
        fresh_until=fresh_until,
        contradicts=contradicts,
        supersedes=supersedes,
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
    assert conflicts[0].tenant_id == "default"
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
    assert proposal.retention_class is RetentionClass.OPERATIONAL


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
    assert "tenant:default" in node.tags


def test_unchanged_source_reingestion_is_idempotent_by_content_hash() -> None:
    fabric = KnowledgeFabric()
    first = source("s1", source_hash="abc")
    second = source("s1", source_hash="abc")

    assert fabric.add_source(first) is first
    assert fabric.add_source(second) is first


def test_changed_source_requires_new_source_identity() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1", source_hash="abc"))

    with pytest.raises(ValueError, match="different content"):
        fabric.add_source(source("s1", source_hash="def"))


def test_tenant_boundary_is_applied_before_retrieval_and_conflict() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("a-source", tenant_id="tenant-a"))
    fabric.add_source(source("b-source", tenant_id="tenant-b"))
    fabric.add_claim(claim("a", "working", source_id="a-source", tenant_id="tenant-a"))
    fabric.add_claim(claim("b", "blocked", source_id="b-source", tenant_id="tenant-b"))

    now = datetime(2026, 9, 3, 1, tzinfo=UTC)
    tenant_a = fabric.retrieval_candidates(tenant_id="tenant-a", now=now)

    assert [item.claim_id for item in tenant_a] == ["a"]
    assert fabric.conflict_groups() == ()


def test_claim_cannot_reference_source_from_another_tenant() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1", tenant_id="tenant-a"))

    with pytest.raises(ValueError, match="another tenant"):
        fabric.add_claim(claim("c1", "working", source_id="s1", tenant_id="tenant-b"))


def test_revoked_source_is_removed_from_retrieval_until_restored() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_claim(claim("c1", "working"))
    now = datetime(2026, 9, 3, 1, tzinfo=UTC)

    initial = fabric.retrieval_candidates(tenant_id="default", now=now)
    assert [item.claim_id for item in initial] == ["c1"]
    fabric.revoke_source("s1")
    assert fabric.retrieval_candidates(tenant_id="default", now=now) == ()
    assert fabric.source_weight(fabric.claims["c1"], now=now) == 0.0
    fabric.restore_source("s1")
    restored = fabric.retrieval_candidates(tenant_id="default", now=now)
    assert [item.claim_id for item in restored] == ["c1"]


def test_stale_claim_is_not_retrieval_eligible() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    item = fabric.add_claim(
        claim("c1", "working", fresh_until="2026-09-03T00:30:00Z")
    )
    now = datetime(2026, 9, 3, 1, tzinfo=UTC)

    assert fabric.claim_is_fresh(item, now=now) is False
    assert fabric.retrieval_candidates(tenant_id="default", now=now) == ()


def test_explicit_supersession_preserves_prior_claim() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1"))
    fabric.add_source(source("s2"))
    fabric.add_claim(claim("old", "candidate", source_id="s1"))
    fabric.add_claim(
        claim("new", "measured", source_id="s2", supersedes=("old",))
    )

    assert "old" in fabric.claims
    assert fabric.claims["new"].supersedes == ("old",)


def test_memory_proposal_cannot_cross_tenant_boundary() -> None:
    fabric = KnowledgeFabric()
    fabric.add_source(source("s1", tenant_id="tenant-a"))
    fabric.add_claim(claim("c1", "working", source_id="s1", tenant_id="tenant-a"))

    with pytest.raises(ValueError, match="another tenant"):
        fabric.propose_memory_write(
            content="remember",
            source_claim_ids=("c1",),
            scope="episodic",
            retention_days=7,
            retention_class=RetentionClass.SESSION,
            tenant_id="tenant-b",
        )
