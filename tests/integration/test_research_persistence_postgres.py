from __future__ import annotations

import os
import uuid

import pytest

from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.knowledge_fabric import (
    ClaimClass,
    KnowledgeClaim,
    SourceClass,
    SourceRecord,
)
from idea_engine.knowledge_repository import PostgresKnowledgeRepository
from idea_engine.research_repository import (
    PostgresResearchRepository,
    ResearchArtifactRecord,
    ResearchContradictionRecord,
    ResearchCoverageMetricRecord,
    ResearchLineageEdgeRecord,
    ResearchSearchAttemptRecord,
)

asyncpg = pytest.importorskip("asyncpg")


@pytest.mark.asyncio
async def test_postgres_research_repository_round_trip() -> None:
    database_url = os.environ.get("CK_KNOWLEDGE_PG_TEST_URL", "").strip()
    if not database_url:
        pytest.skip("CK_KNOWLEDGE_PG_TEST_URL is not configured")

    tenant_id = "research-it-" + uuid.uuid4().hex
    source_ids = ("source-1", "source-2")
    claim_ids = ("claim-1", "claim-2")
    artifact_id = "artifact-1"

    pool = await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=2,
        timeout=5,
    )
    config = RuntimeBindingConfig(
        database_url=database_url,
        redis_url="redis://127.0.0.1:1/0",
    )
    knowledge_repo = PostgresKnowledgeRepository(pool, config)
    research_repo = PostgresResearchRepository(pool, config)
    schema_verified = False

    try:
        await knowledge_repo.verify_schema()
        await research_repo.verify_schema()
        schema_verified = True

        for source_id in source_ids:
            await knowledge_repo.store_source(
                SourceRecord(
                    source_id=source_id,
                    source_class=SourceClass.RESEARCH,
                    locator=f"https://example.test/{source_id}",
                    title=source_id,
                    retrieved_at="2026-09-07T00:00:00Z",
                    trust_score=0.9,
                    tenant_id=tenant_id,
                    source_hash=f"hash-{source_id}",
                    metadata={"source_version": "v1"},
                )
            )

        await knowledge_repo.store_claim(
            KnowledgeClaim(
                claim_id=claim_ids[0],
                subject="CK-NEXUS",
                predicate="research-state",
                value="candidate-a",
                claim_class=ClaimClass.FACT,
                source_ids=(source_ids[0],),
                confidence=0.8,
                observed_at="2026-09-07T00:00:00Z",
                tenant_id=tenant_id,
            )
        )
        await knowledge_repo.store_claim(
            KnowledgeClaim(
                claim_id=claim_ids[1],
                subject="CK-NEXUS",
                predicate="research-state",
                value="candidate-b",
                claim_class=ClaimClass.FACT,
                source_ids=(source_ids[1],),
                confidence=0.8,
                observed_at="2026-09-07T00:00:00Z",
                tenant_id=tenant_id,
            )
        )

        artifact = ResearchArtifactRecord(
            tenant_id=tenant_id,
            artifact_id=artifact_id,
            decision="CONTINUE_RESEARCH",
            truth_state="MEASURED_NOT_VERIFIED",
            ready_for_analysis=False,
            scope={"languages": ["en", "th"]},
            gaps=(
                {
                    "kind": "contradiction",
                    "severity": "high",
                },
            ),
            source_ids=source_ids,
            claim_ids=claim_ids,
            lineage_edges=(
                ResearchLineageEdgeRecord(
                    edge_id="edge-1",
                    from_node_kind="CLAIM",
                    from_node_id=claim_ids[0],
                    to_node_kind="SOURCE",
                    to_node_id=source_ids[0],
                    edge_type="DERIVED_FROM",
                    independent_validation=True,
                ),
            ),
            contradictions=(
                ResearchContradictionRecord(
                    contradiction_id="contradiction-1",
                    contradiction_type="FACTUAL",
                    resolution_status="RESEARCH_REQUIRED",
                    confidence=0.9,
                    claim_ids=claim_ids,
                ),
            ),
            search_attempts=(
                ResearchSearchAttemptRecord(
                    attempt_id="attempt-1",
                    query="CK-NEXUS research state",
                    engine="searxng",
                    result_count=2,
                    duration_ms=25,
                    status="SUCCESS",
                ),
            ),
            coverage_metrics=(
                ResearchCoverageMetricRecord(
                    metric_id="coverage-1",
                    dimension="language",
                    coverage_fraction=0.5,
                ),
            ),
        )

        assert await research_repo.store_artifact(artifact) is True
        assert await research_repo.store_artifact(artifact) is False

        loaded = await research_repo.load_artifact(
            tenant_id=tenant_id,
            artifact_id=artifact_id,
        )
        assert loaded == artifact
        assert loaded.truth_state == "MEASURED_NOT_VERIFIED"
    finally:
        if schema_verified:
            async with (
                pool.acquire() as conn,
                conn.transaction(),
            ):
                await conn.execute(
                    """
                    DELETE FROM knowledge_research_artifacts
                    WHERE tenant_id = $1
                    """,
                    tenant_id,
                )
                await conn.execute(
                    "DELETE FROM knowledge_claims WHERE tenant_id = $1",
                    tenant_id,
                )
                await conn.execute(
                    "DELETE FROM knowledge_sources WHERE tenant_id = $1",
                    tenant_id,
                )
        await pool.close()
