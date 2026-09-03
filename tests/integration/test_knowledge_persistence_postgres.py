from __future__ import annotations

import os
import uuid

import pytest

from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.knowledge_fabric import (
    ClaimClass,
    KnowledgeClaim,
    KnowledgeFabric,
    SourceClass,
    SourceRecord,
)
from idea_engine.knowledge_repository import PostgresKnowledgeRepository

asyncpg = pytest.importorskip("asyncpg")


@pytest.mark.asyncio
async def test_postgres_knowledge_repository_round_trip() -> None:
    database_url = os.environ.get("CK_KNOWLEDGE_PG_TEST_URL", "").strip()
    if not database_url:
        pytest.skip("CK_KNOWLEDGE_PG_TEST_URL is not configured")

    tenant_id = "knowledge-it-" + uuid.uuid4().hex
    source_id = "source-1"
    claim_id = "claim-1"
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2, timeout=5)
    config = RuntimeBindingConfig(
        database_url=database_url,
        redis_url="redis://127.0.0.1:1/0",
    )
    repository = PostgresKnowledgeRepository(pool, config)

    try:
        await repository.verify_schema()
        source = SourceRecord(
            source_id=source_id,
            source_class=SourceClass.RESEARCH,
            locator="https://example.test/integration",
            title="integration",
            retrieved_at="2026-09-03T00:00:00Z",
            trust_score=0.9,
            tenant_id=tenant_id,
            source_hash="integration-hash",
            metadata={"source_version": "v1"},
        )
        claim = KnowledgeClaim(
            claim_id=claim_id,
            subject="CK-NEXUS",
            predicate="integration-state",
            value="working",
            claim_class=ClaimClass.FACT,
            source_ids=(source_id,),
            confidence=0.8,
            observed_at="2026-09-03T00:00:00Z",
            tenant_id=tenant_id,
        )

        assert await repository.store_source(source) is True
        assert await repository.store_source(source) is False
        await repository.store_claim(claim)
        await repository.set_source_revoked(
            tenant_id=tenant_id,
            source_id=source_id,
            revoked=True,
        )

        sources, claims, revoked = await repository.load_tenant(tenant_id)
        assert sources == (source,)
        assert claims == (claim,)
        assert revoked == frozenset({source_id})

        fabric = KnowledgeFabric()
        fabric.add_source(sources[0])
        fabric.add_claim(claims[0])
        proposal = fabric.propose_memory_write(
            content="integration observation",
            source_claim_ids=(claim_id,),
            scope="episodic",
            retention_days=7,
            tenant_id=tenant_id,
        )
        await repository.store_memory_proposal(proposal)
    finally:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM knowledge_memory_proposals WHERE tenant_id = $1",
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
