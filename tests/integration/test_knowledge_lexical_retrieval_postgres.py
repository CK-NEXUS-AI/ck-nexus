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

asyncpg = pytest.importorskip("asyncpg")


@pytest.mark.asyncio
async def test_postgres_lexical_retrieval_round_trip() -> None:
    database_url = os.environ.get("CK_KNOWLEDGE_PG_TEST_URL", "").strip()
    if not database_url:
        pytest.skip("CK_KNOWLEDGE_PG_TEST_URL is not configured")

    tenant_id = "lexical-it-" + uuid.uuid4().hex
    source_id = "source-1"
    claim_id = "claim-1"
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
    repository = PostgresKnowledgeRepository(pool, config)

    try:
        source = SourceRecord(
            source_id=source_id,
            source_class=SourceClass.RESEARCH,
            locator="https://example.test/lexical",
            title="lexical integration",
            retrieved_at="2026-09-04T00:00:00Z",
            trust_score=0.9,
            tenant_id=tenant_id,
            source_hash="lexical-integration-hash",
            metadata={"source_version": "v1"},
        )
        claim = KnowledgeClaim(
            claim_id=claim_id,
            subject="CK-NEXUS",
            predicate="retrieval-state",
            value="lexical retrieval working",
            claim_class=ClaimClass.FACT,
            source_ids=(source_id,),
            confidence=0.8,
            observed_at="2026-09-04T00:00:00Z",
            tenant_id=tenant_id,
        )

        assert await repository.store_source(source) is True
        await repository.store_claim(claim)

        hits = await repository.search_claims(
            tenant_id=tenant_id,
            query='"lexical retrieval" working',
        )
        assert tuple(hit.claim_id for hit in hits) == (claim_id,)
        assert hits[0].source_ids == (source_id,)

        await repository.set_source_revoked(
            tenant_id=tenant_id,
            source_id=source_id,
            revoked=True,
        )
        assert (
            await repository.search_claims(
                tenant_id=tenant_id,
                query="lexical retrieval",
            )
            == ()
        )
    finally:
        async with (
            pool.acquire() as conn,
            conn.transaction(),
        ):
            await conn.execute(
                "DELETE FROM knowledge_claims WHERE tenant_id = $1",
                tenant_id,
            )
            await conn.execute(
                "DELETE FROM knowledge_sources WHERE tenant_id = $1",
                tenant_id,
            )
        await pool.close()
