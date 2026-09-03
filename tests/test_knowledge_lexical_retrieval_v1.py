from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest

import idea_engine.knowledge_repository as repository_module
from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.knowledge_repository import PostgresKnowledgeRepository


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.calls.append((sql, args))
        return self.rows


class FakePool:
    pass


def runtime_config() -> RuntimeBindingConfig:
    return RuntimeBindingConfig(
        database_url="postgresql://example.invalid/cknexus",
        redis_url="redis://example.invalid/0",
    )


def install_connection(
    monkeypatch: pytest.MonkeyPatch,
    conn: FakeConnection,
) -> None:
    @asynccontextmanager
    async def fake_acquire(_pool: Any, _cfg: RuntimeBindingConfig):
        yield conn

    monkeypatch.setattr(repository_module, "acquire_db_connection", fake_acquire)


@pytest.mark.asyncio
async def test_search_claims_is_tenant_scoped_revocation_aware_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection(
        [
            {
                "claim_id": "c1",
                "subject": "CK-NEXUS",
                "predicate": "runtime-state",
                "payload": {"value": "working"},
                "observed_at": datetime(2026, 9, 3, tzinfo=UTC),
                "fresh_until": None,
                "score": 0.375,
                "source_ids": ["s1", "s2"],
            }
        ]
    )
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    hits = await repo.search_claims(
        tenant_id="tenant-a",
        query="runtime working",
        limit=5,
    )

    assert len(hits) == 1
    assert hits[0].claim_id == "c1"
    assert hits[0].source_ids == ("s1", "s2")
    assert hits[0].score == 0.375
    sql, args = conn.calls[0]
    assert args == ("tenant-a", "runtime working", 5)
    assert "websearch_to_tsquery" in sql
    assert "ks.revoked = FALSE" in sql
    assert "c.fresh_until IS NULL OR c.fresh_until >= now()" in sql
    assert "ORDER BY score DESC, c.observed_at DESC, c.claim_id ASC" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tenant_id", "query", "limit", "message"),
    [
        ("", "working", 10, "tenant_id is required"),
        ("tenant-a", "", 10, "query is required"),
        ("tenant-a", "x", 0, "limit must be between 1 and 100"),
        ("tenant-a", "x", 101, "limit must be between 1 and 100"),
    ],
)
async def test_search_claims_rejects_invalid_bounds(
    tenant_id: str,
    query: str,
    limit: int,
    message: str,
) -> None:
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(ValueError, match=message):
        await repo.search_claims(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
        )


@pytest.mark.asyncio
async def test_search_claims_rejects_oversized_query() -> None:
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(ValueError, match="query must be <= 512 characters"):
        await repo.search_claims(
            tenant_id="tenant-a",
            query="x" * 513,
        )
