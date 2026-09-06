from __future__ import annotations

from dataclasses import replace

import pytest
from idea_engine.knowledge_fabric import (
    ClaimClass,
    VerificationState,
)

from creator_app.global_knowledge.contracts import (
    Claim,
    Reliability,
    SourceKind,
    SourceRef,
)
from creator_app.global_knowledge.research_intelligence import (
    ClaimObservation,
    ResearchRequirements,
    SourceObservation,
    compile_research_artifact,
    decide_research_cycle,
)
from creator_app.global_knowledge.research_persistence_bridge import (
    artifact_to_record,
    claim_to_record,
    source_ref_to_record,
)


def source(source_id: str, *, language: str = "en") -> SourceRef:
    return SourceRef(
        source_id=source_id,
        url=f"https://example.test/{source_id}",
        canonical_url=f"https://example.test/{source_id}",
        source_kind=SourceKind.PUBLIC_DOCUMENT,
        language=language,
        region="global",
        observed_at="2026-09-07T00:00:00Z",
        content_hash=f"hash-{source_id}",
        title=source_id,
    )


def claim(claim_id: str, source_id: str) -> Claim:
    return Claim(
        claim_id=claim_id,
        subject="CK-NEXUS",
        predicate="research_state",
        object_value="candidate",
        source_ids=(source_id,),
        confidence=0.8,
        reliability=Reliability.OBSERVED,
        observed_at="2026-09-07T00:00:00Z",
    )


def compiled_fixture():
    sources = (source("s1"), source("s2"))
    claims = (claim("c1", "s1"),)
    observations = (
        SourceObservation(
            source=sources[0],
            lineage_id="l1",
            is_primary=True,
        ),
        SourceObservation(
            source=sources[1],
            lineage_id="l2",
            independent_validation=True,
        ),
    )
    artifact = compile_research_artifact(
        observations,
        (ClaimObservation(claim=claims[0]),),
        ResearchRequirements(
            min_sources=2,
            min_independent_lineages=2,
            min_primary_sources=1,
        ),
    )
    decision = decide_research_cycle(artifact)
    return sources, claims, artifact, decision


def test_source_bridge_requires_explicit_trust_score() -> None:
    record = source_ref_to_record(
        source("s1"),
        tenant_id="tenant-a",
        trust_score=0.75,
    )

    assert record.tenant_id == "tenant-a"
    assert record.trust_score == 0.75
    assert record.source_hash == "hash-s1"
    assert record.metadata["original_source_kind"] == "public_document"


def test_claim_bridge_never_promotes_verification() -> None:
    record = claim_to_record(
        claim("c1", "s1"),
        tenant_id="tenant-a",
        claim_class=ClaimClass.FACT,
    )

    assert record.verification is VerificationState.OBSERVED
    assert record.tenant_id == "tenant-a"


def test_artifact_bridge_maps_measured_state_and_lineage() -> None:
    _sources, claims, artifact, decision = compiled_fixture()

    record = artifact_to_record(
        artifact,
        decision,
        tenant_id="tenant-a",
        artifact_id="artifact-1",
        scope={"query": "ck nexus"},
        claims=claims,
    )

    assert record.decision == "READY_FOR_ANALYSIS"
    assert record.truth_state == "MEASURED_NOT_VERIFIED"
    assert record.ready_for_analysis is True
    assert len(record.lineage_edges) == 1
    assert record.lineage_edges[0].edge_type == "DERIVED_FROM"
    assert any(
        metric.dimension == "overall_scoped"
        for metric in record.coverage_metrics
    )


def test_artifact_bridge_rejects_verified_worker_artifact() -> None:
    _sources, claims, artifact, decision = compiled_fixture()
    verified = replace(artifact, verified=True)

    with pytest.raises(PermissionError, match="VERIFIED worker"):
        artifact_to_record(
            verified,
            decision,
            tenant_id="tenant-a",
            artifact_id="artifact-1",
            scope={},
            claims=claims,
        )


def test_artifact_bridge_rejects_claim_source_outside_artifact() -> None:
    _sources, claims, artifact, decision = compiled_fixture()
    bad_claim = replace(claims[0], source_ids=("outside",))

    with pytest.raises(ValueError, match="outside research artifact"):
        artifact_to_record(
            artifact,
            decision,
            tenant_id="tenant-a",
            artifact_id="artifact-1",
            scope={},
            claims=(bad_claim,),
        )
