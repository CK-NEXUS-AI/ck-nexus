from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

import pytest

import idea_engine.research_repository as repository_module
from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.research_repository import (
    PostgresResearchRepository,
    ResearchArtifactRecord,
    ResearchContradictionRecord,
    ResearchCoverageMetricRecord,
    ResearchLineageEdgeRecord,
    ResearchSearchAttemptRecord,
)


def runtime_config() -> RuntimeBindingConfig:
    return RuntimeBindingConfig(
        database_url="postgresql://example.invalid/cknexus",
        redis_url="redis://example.invalid/0",
    )


def artifact() -> ResearchArtifactRecord:
    return ResearchArtifactRecord(
        tenant_id="tenant-a",
        artifact_id="research-1",
        decision="CONTINUE_RESEARCH",
        truth_state="MEASURED_NOT_VERIFIED",
        ready_for_analysis=False,
        scope={"languages": ["en", "th"]},
        gaps=(
            {
                "kind": "coverage",
                "severity": "medium",
                "reason": "missing_language",
            },
        ),
        source_ids=("s1", "s2"),
        claim_ids=("c1", "c2"),
        lineage_edges=(
            ResearchLineageEdgeRecord(
                edge_id="e1",
                from_node_kind="CLAIM",
                from_node_id="c1",
                to_node_kind="SOURCE",
                to_node_id="s1",
                edge_type="DERIVED_FROM",
                independent_validation=True,
            ),
        ),
        contradictions=(
            ResearchContradictionRecord(
                contradiction_id="x1",
                contradiction_type="FACTUAL",
                resolution_status="RESEARCH_REQUIRED",
                confidence=0.9,
                claim_ids=("c1", "c2"),
            ),
        ),
        search_attempts=(
            ResearchSearchAttemptRecord(
                attempt_id="a1",
                query="ck nexus",
                engine="searxng",
                result_count=7,
                duration_ms=120,
                status="SUCCESS",
            ),
        ),
        coverage_metrics=(
            ResearchCoverageMetricRecord(
                metric_id="m1",
                dimension="language",
                coverage_fraction=0.5,
            ),
        ),
    )


class Transaction:
    async def __aenter__(self) -> Transaction:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.fetchrow_results: list[Any] = []
        self.fetchval_results: list[Any] = []
        self.fetch_results: list[list[dict[str, Any]]] = []
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.executemany_calls: list[tuple[str, list[tuple[Any, ...]]]] = []

    def transaction(self) -> Transaction:
        return Transaction()

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        self.executed.append((sql, args))
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetchval(self, sql: str, *args: Any) -> Any:
        self.executed.append((sql, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else None

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.executed.append((sql, args))
        return self.fetch_results.pop(0) if self.fetch_results else []

    async def execute(self, sql: str, *args: Any) -> str:
        self.executed.append((sql, args))
        return "INSERT 0 1"

    async def executemany(
        self,
        sql: str,
        args: list[tuple[Any, ...]],
    ) -> None:
        self.executemany_calls.append((sql, args))


class FakePool:
    pass


def install_connection(
    monkeypatch: pytest.MonkeyPatch,
    conn: FakeConnection,
) -> None:
    @asynccontextmanager
    async def fake_acquire(_pool: Any, _cfg: RuntimeBindingConfig):
        yield conn

    monkeypatch.setattr(
        repository_module,
        "acquire_db_connection",
        fake_acquire,
    )


def test_research_artifact_rejects_verified_storage_state() -> None:
    with pytest.raises(PermissionError, match="cannot persist VERIFIED"):
        replace(artifact(), truth_state="VERIFIED")


def test_research_contract_rejects_invalid_contradiction_state() -> None:
    with pytest.raises(ValueError, match="unsupported resolution_status"):
        ResearchContradictionRecord(
            contradiction_id="bad",
            contradiction_type="FACTUAL",
            resolution_status="AUTO_APPROVED",
            confidence=0.5,
            claim_ids=("c1", "c2"),
        )


@pytest.mark.asyncio
async def test_verify_schema_fails_closed_when_table_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchval_results = [
        "knowledge_research_artifacts",
        None,
        "x",
        "x",
        "x",
        "x",
        "x",
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    with pytest.raises(
        RuntimeError,
        match="knowledge_research_artifact_sources",
    ):
        await repo.verify_schema()


@pytest.mark.asyncio
async def test_store_artifact_validates_tenant_scoped_references_and_inserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchrow_results = [None]
    conn.fetch_results = [
        [{"source_id": "s1"}, {"source_id": "s2"}],
        [{"claim_id": "c1"}, {"claim_id": "c2"}],
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    inserted = await repo.store_artifact(artifact())

    assert inserted is True
    assert any(
        "INSERT INTO knowledge_research_artifacts" in sql
        for sql, _args in conn.executed
    )
    assert len(conn.executemany_calls) == 6


@pytest.mark.asyncio
async def test_store_artifact_rejects_missing_source_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchrow_results = [None]
    conn.fetch_results = [
        [{"source_id": "s1"}],
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    with pytest.raises(
        ValueError,
        match="unknown research source ids",
    ):
        await repo.store_artifact(artifact())


@pytest.mark.asyncio
async def test_store_artifact_rejects_unknown_lineage_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = replace(
        artifact(),
        lineage_edges=(
            ResearchLineageEdgeRecord(
                edge_id="bad-edge",
                from_node_kind="SOURCE",
                from_node_id="missing",
                to_node_kind="CLAIM",
                to_node_id="c1",
                edge_type="SUPPORTS",
            ),
        ),
    )
    conn = FakeConnection()
    conn.fetchrow_results = [None]
    conn.fetch_results = [
        [{"source_id": "s1"}, {"source_id": "s2"}],
        [{"claim_id": "c1"}, {"claim_id": "c2"}],
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    with pytest.raises(
        ValueError,
        match="unknown from node",
    ):
        await repo.store_artifact(item)


@pytest.mark.asyncio
async def test_store_artifact_same_payload_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = artifact()
    conn = FakeConnection()
    conn.fetchrow_results = [
        {"payload": repository_module._json_payload(item)}
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    inserted = await repo.store_artifact(item)

    assert inserted is False
    assert not any(
        "INSERT INTO knowledge_research_artifacts" in sql
        for sql, _args in conn.executed
    )


@pytest.mark.asyncio
async def test_store_artifact_rejects_same_id_with_different_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = artifact()
    old = replace(item, decision="READY_FOR_ANALYSIS")
    conn = FakeConnection()
    conn.fetchrow_results = [
        {"payload": repository_module._json_payload(old)}
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    with pytest.raises(ValueError, match="different payload"):
        await repo.store_artifact(item)


@pytest.mark.asyncio
async def test_load_artifact_round_trip_from_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = artifact()
    conn = FakeConnection()
    conn.fetchrow_results = [
        {"payload": repository_module._json_payload(item)}
    ]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    loaded = await repo.load_artifact(
        tenant_id="tenant-a",
        artifact_id="research-1",
    )

    assert loaded == item
    assert conn.executed[-1][1] == ("tenant-a", "research-1")


@pytest.mark.asyncio
async def test_load_artifact_fails_for_unknown_tenant_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConnection()
    conn.fetchrow_results = [None]
    install_connection(monkeypatch, conn)
    repo = PostgresResearchRepository(FakePool(), runtime_config())

    with pytest.raises(KeyError, match="unknown research artifact"):
        await repo.load_artifact(
            tenant_id="tenant-b",
            artifact_id="research-1",
        )
