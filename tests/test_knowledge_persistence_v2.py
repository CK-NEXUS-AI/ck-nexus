from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

import pytest
from idea_engine.knowledge_fabric import (
    ClaimClass,
    KnowledgeClaim,
    MemoryWriteProposal,
    RetentionClass,
    SourceClass,
    SourceRecord,
)

import idea_engine.knowledge_repository as repository_module
from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.knowledge_repository import PostgresKnowledgeRepository


def runtime_config() -> RuntimeBindingConfig:
    return RuntimeBindingConfig(
        database_url="postgresql://example.invalid/cknexus",
        redis_url="redis://example.invalid/0",
    )


def source(
    source_id: str = "s1",
    *,
    tenant_id: str = "tenant-a",
    source_hash: str | None = "hash-a",
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        source_class=SourceClass.RESEARCH,
        locator=f"https://example.test/{source_id}",
        title=source_id,
        retrieved_at="2026-09-03T00:00:00Z",
        trust_score=0.9,
        tenant_id=tenant_id,
        source_hash=source_hash,
        metadata={"source_version": "v1"},
    )


def claim(
    claim_id: str = "c1",
    *,
    tenant_id: str = "tenant-a",
    source_ids: tuple[str, ...] = ("s1",),
    contradicts: tuple[str, ...] = (),
    supersedes: tuple[str, ...] = (),
) -> KnowledgeClaim:
    return KnowledgeClaim(
        claim_id=claim_id,
        subject="CK-NEXUS",
        predicate="runtime-state",
        value="working",
        claim_class=ClaimClass.FACT,
        source_ids=source_ids,
        confidence=0.8,
        observed_at="2026-09-03T00:00:00Z",
        tenant_id=tenant_id,
        contradicts=contradicts,
        supersedes=supersedes,
    )


class Transaction:
    async def __aenter__(self) -> Transaction:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.fetchrow_result: Any = None
        self.fetchval_results: list[Any] = []
        self.fetch_results: list[list[dict[str, Any]]] = []
        self.execute_results: list[str] = []
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.executemany_calls: list[tuple[str, list[tuple[Any, ...]]]] = []

    def transaction(self) -> Transaction:
        return Transaction()

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        self.executed.append((sql, args))
        return self.fetchrow_result

    async def fetchval(self, sql: str, *args: Any) -> Any:
        self.executed.append((sql, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.executed.append((sql, args))
        return self.fetch_results.pop(0) if self.fetch_results else []

    async def execute(self, sql: str, *args: Any) -> str:
        self.executed.append((sql, args))
        return self.execute_results.pop(0) if self.execute_results else "INSERT 0 1"

    async def executemany(self, sql: str, args: list[tuple[Any, ...]]) -> None:
        self.executemany_calls.append((sql, args))


class FakePool:
    pass


def install_connection(monkeypatch: pytest.MonkeyPatch, conn: FakeConnection) -> None:
    @asynccontextmanager
    async def fake_acquire(_pool: Any, _cfg: RuntimeBindingConfig):
        yield conn

    monkeypatch.setattr(repository_module, "acquire_db_connection", fake_acquire)


@pytest.mark.asyncio
async def test_verify_schema_fails_closed_when_table_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchval_results = ["knowledge_sources", None, "x", "x", "x", "x"]
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(RuntimeError, match="knowledge_claims"):
        await repo.verify_schema()


@pytest.mark.asyncio
async def test_store_source_inserts_tenant_scoped_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    inserted = await repo.store_source(source())

    assert inserted is True
    assert any("INSERT INTO knowledge_sources" in sql for sql, _args in conn.executed)
    insert_args = next(
        args
        for sql, args in conn.executed
        if "INSERT INTO knowledge_sources" in sql
    )
    assert insert_args[:2] == ("tenant-a", "s1")


@pytest.mark.asyncio
async def test_store_source_same_payload_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    item = source()
    conn.fetchrow_result = {
        "source_hash": item.source_hash,
        "source_version": "v1",
        "payload": repository_module._json_payload(item),
    }
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    inserted = await repo.store_source(item)

    assert inserted is False
    assert not any("INSERT INTO knowledge_sources" in sql for sql, _args in conn.executed)


@pytest.mark.asyncio
async def test_store_source_rejects_same_identity_with_different_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    item = source()
    old_payload = repository_module._json_payload(
        replace(item, source_hash="different", title="old")
    )
    conn.fetchrow_result = {
        "source_hash": "different",
        "source_version": "v1",
        "payload": old_payload,
    }
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(ValueError, match="different content"):
        await repo.store_source(item)


@pytest.mark.asyncio
async def test_store_claim_rejects_missing_tenant_scoped_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchval_results = [None]
    conn.fetch_results = [[]]
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(ValueError, match="unknown source_ids for tenant"):
        await repo.store_claim(claim())


@pytest.mark.asyncio
async def test_store_claim_persists_source_and_relation_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchval_results = [None]
    conn.fetch_results = [
        [{"source_id": "s1"}],
        [{"claim_id": "old"}],
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    await repo.store_claim(claim(claim_id="new", supersedes=("old",)))

    assert any("INSERT INTO knowledge_claims" in sql for sql, _args in conn.executed)
    assert len(conn.executemany_calls) == 2
    assert conn.executemany_calls[0][1] == [("tenant-a", "new", "s1")]
    assert conn.executemany_calls[1][1] == [
        ("tenant-a", "new", "supersedes", "old")
    ]


@pytest.mark.asyncio
async def test_revocation_is_tenant_scoped_and_fails_for_unknown_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.execute_results = ["UPDATE 0"]
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    with pytest.raises(KeyError, match="unknown source_id for tenant"):
        await repo.set_source_revoked(
            tenant_id="tenant-b",
            source_id="s1",
            revoked=True,
        )

    _sql, args = conn.executed[-1]
    assert args[:2] == ("tenant-b", "s1")


@pytest.mark.asyncio
async def test_memory_repository_never_accepts_auto_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())
    proposal = MemoryWriteProposal(
        proposal_id="p1",
        tenant_id="tenant-a",
        content="remember this",
        source_claim_ids=("c1",),
        scope="episodic",
        retention_days=30,
        retention_class=RetentionClass.OPERATIONAL,
        auto_approved=True,
    )

    with pytest.raises(PermissionError, match="auto-approved"):
        await repo.store_memory_proposal(proposal)


@pytest.mark.asyncio
async def test_load_tenant_reconstructs_only_requested_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    item_source = source()
    item_claim = claim()
    conn.fetch_results = [
        [
            {
                "source_id": "s1",
                "revoked": True,
                "payload": repository_module._json_payload(item_source),
            }
        ],
        [
            {
                "claim_id": "c1",
                "payload": repository_module._json_payload(item_claim),
            }
        ],
        [{"claim_id": "c1", "source_id": "s1"}],
        [],
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresKnowledgeRepository(FakePool(), runtime_config())

    sources, claims, revoked = await repo.load_tenant("tenant-a")

    assert sources == (item_source,)
    assert claims == (item_claim,)
    assert revoked == frozenset({"s1"})
    assert all(args == ("tenant-a",) for _sql, args in conn.executed)
