[Reading 221 lines from start (total: 221 lines, 0 remaining)]

"""Bridge research intelligence artifacts into canonical PostgreSQL records.

This module reconciles the Gen 6 research contracts with the existing
Knowledge Persistence V2 / Research Persistence V1 records. It is a
translation boundary only and has no verification or approval authority.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from idea_engine.knowledge_fabric import (
    CanonicalSourceKind,
    ClaimClass,
    KnowledgeClaim,
    SourceClass,
    SourceRecord,
    VerificationState,
)

from creator_app.global_knowledge.contracts import Claim, SourceRef
from creator_app.global_knowledge.research_intelligence import (
    ResearchCompilationArtifact,
    ResearchCycleAction,
    ResearchCycleDecision,
)
from idea_engine.research_repository import (
    ResearchArtifactRecord,
    ResearchContradictionRecord,
    ResearchCoverageMetricRecord,
    ResearchLineageEdgeRecord,
)


def source_ref_to_record(
    source: SourceRef,
    *,
    tenant_id: str,
    trust_score: float,
) -> SourceRecord:
    """Convert a discovered source without inventing trust."""

    return SourceRecord(
        source_id=source.source_id,
        source_class=SourceClass.RESEARCH,
        locator=source.canonical_url or source.url,
        title=source.title or source.canonical_url or source.url,
        retrieved_at=source.observed_at,
        trust_score=trust_score,
        tenant_id=tenant_id,
        source_kind=CanonicalSourceKind.PUBLIC_DOCUMENTATION,
        language=source.language,
        author=source.author,
        published_at=source.published_at,
        rights=source.license_hint or "unknown",
        source_hash=source.content_hash,
        producer="ck-nexus-global-knowledge",
        transformation_chain=("global_knowledge_source_ref",),
        metadata={
            "original_source_kind": source.source_kind.value,
            "region": source.region,
            "canonical_url": source.canonical_url,
        },
    )


def claim_to_record(
    claim: Claim,
    *,
    tenant_id: str,
    claim_class: ClaimClass,
) -> KnowledgeClaim:
    """Convert a research claim without promoting its verification state."""

    return KnowledgeClaim(
        claim_id=claim.claim_id,
        subject=claim.subject,
        predicate=claim.predicate,
        value=claim.object_value,
        claim_class=claim_class,
        source_ids=claim.source_ids,
        confidence=claim.confidence,
        observed_at=claim.observed_at,
        tenant_id=tenant_id,
        verification=VerificationState.OBSERVED,
        valid_from=claim.valid_from,
        qualifiers={
            str(key): str(value)
            for key, value in claim.qualifiers.items()
        },
    )


def artifact_to_record(
    artifact: ResearchCompilationArtifact,
    decision: ResearchCycleDecision,
    *,
    tenant_id: str,
    artifact_id: str,
    scope: dict[str, Any],
    claims: tuple[Claim, ...],
) -> ResearchArtifactRecord:
    """Translate a measured research artifact into persistence form."""

    if artifact.verified:
        raise PermissionError(
            "research bridge cannot persist a VERIFIED worker artifact"
        )

    claim_by_id = {claim.claim_id: claim for claim in claims}
    if set(claim_by_id) != set(artifact.claim_ids):
        raise ValueError("claims must exactly match artifact claim_ids")

    source_ids = set(artifact.source_ids)
    lineage_edges: list[ResearchLineageEdgeRecord] = []
    for claim in claims:
        for source_id in claim.source_ids:
            if source_id not in source_ids:
                raise ValueError(
                    "claim references source outside research artifact"
                )
            lineage_edges.append(
                ResearchLineageEdgeRecord(
                    edge_id=_stable_id(
                        "edge",
                        artifact_id,
                        claim.claim_id,
                        source_id,
                    ),
                    from_node_kind="CLAIM",
                    from_node_id=claim.claim_id,
                    to_node_kind="SOURCE",
                    to_node_id=source_id,
                    edge_type="DERIVED_FROM",
                    independent_validation=False,
                )
            )

    resolution_status = (
        "HUMAN_REVIEW_REQUIRED"
        if decision.action is ResearchCycleAction.HUMAN_REVIEW_REQUIRED
        else "RESEARCH_REQUIRED"
    )
    contradictions = tuple(
        ResearchContradictionRecord(
            contradiction_id=_stable_id(
                "contradiction",
                artifact_id,
                item.contradiction_type.value,
                *sorted(item.claim_ids),
            ),
            contradiction_type=item.contradiction_type.name,
            resolution_status=resolution_status,
            confidence=item.confidence,
            claim_ids=item.claim_ids,
        )
        for item in artifact.contradictions
    )

    truth_state = (
        "REVIEW_REQUIRED"
        if decision.action is ResearchCycleAction.HUMAN_REVIEW_REQUIRED
        else "MEASURED_NOT_VERIFIED"
    )

    return ResearchArtifactRecord(
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        decision=decision.action.name,
        truth_state=truth_state,
        ready_for_analysis=artifact.ready_for_analysis,
        scope=dict(scope),
        gaps=tuple(asdict(gap) for gap in artifact.gaps),
        source_ids=artifact.source_ids,
        claim_ids=artifact.claim_ids,
        lineage_edges=tuple(lineage_edges),
        contradictions=contradictions,
        coverage_metrics=_coverage_metrics(
            artifact_id,
            artifact,
        ),
    )


def _coverage_metrics(
    artifact_id: str,
    artifact: ResearchCompilationArtifact,
) -> tuple[ResearchCoverageMetricRecord, ...]:
    values = {
        "source": artifact.coverage.source_coverage,
        "lineage": artifact.coverage.lineage_coverage,
        "primary_source": artifact.coverage.primary_source_coverage,
        "language": artifact.coverage.language_coverage,
        "region": artifact.coverage.region_coverage,
        "source_kind": artifact.coverage.source_kind_coverage,
        "technical": artifact.coverage.technical_coverage,
        "freshness": artifact.coverage.freshness_coverage,
        "overall_scoped": artifact.coverage.overall_scoped_coverage,
    }
    return tuple(
        ResearchCoverageMetricRecord(
            metric_id=_stable_id(
                "coverage",
                artifact_id,
                dimension,
            ),
            dimension=dimension,
            coverage_fraction=value,
            scoped=True,
        )
        for dimension, value in values.items()
        if value is not None
    )


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"{prefix}-{digest}"

[executed on device: 10616a96dd5c121bb (99b698de-7e79-4f9c-ad45-281a8377dada)]