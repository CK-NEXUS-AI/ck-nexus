[Reading 654 lines from start (total: 654 lines, 0 remaining)]

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from creator_app.runtime_binding import (
    RuntimeBindingConfig,
    acquire_db_connection,
    get_db_pool,
)

_ALLOWED_DECISIONS = frozenset(
    {
        "CONTINUE_RESEARCH",
        "READY_FOR_ANALYSIS",
        "HUMAN_REVIEW_REQUIRED",
    }
)
_ALLOWED_TRUTH_STATES = frozenset(
    {
        "DISCOVERED",
        "PLANNED",
        "EXECUTED",
        "MEASURED",
        "REVIEW_REQUIRED",
        "MEASURED_NOT_VERIFIED",
        "BLOCKED",
        "FAILED",
    }
)
_ALLOWED_NODE_KINDS = frozenset({"SOURCE", "CLAIM"})
_ALLOWED_EDGE_TYPES = frozenset(
    {
        "CITES",
        "DERIVED_FROM",
        "SUPPORTS",
        "CONTRADICTS",
    }
)
_ALLOWED_CONTRADICTION_TYPES = frozenset(
    {
        "FACTUAL",
        "TEMPORAL",
        "LOGICAL_REVIEW_REQUIRED",
    }
)
_ALLOWED_RESOLUTION_STATES = frozenset(
    {
        "UNRESOLVED",
        "RESEARCH_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
        "RESOLVED",
    }
)


@dataclass(frozen=True, slots=True)
class ResearchLineageEdgeRecord:
    edge_id: str
    from_node_kind: str
    from_node_id: str
    to_node_kind: str
    to_node_id: str
    edge_type: str
    independent_validation: bool = False

    def __post_init__(self) -> None:
        if not self.edge_id.strip():
            raise ValueError("edge_id is required")
        if not self.from_node_id.strip() or not self.to_node_id.strip():
            raise ValueError("lineage node ids are required")
        if self.from_node_kind not in _ALLOWED_NODE_KINDS:
            raise ValueError("unsupported from_node_kind")
        if self.to_node_kind not in _ALLOWED_NODE_KINDS:
            raise ValueError("unsupported to_node_kind")
        if self.edge_type not in _ALLOWED_EDGE_TYPES:
            raise ValueError("unsupported edge_type")
        if (
            self.from_node_kind == self.to_node_kind
            and self.from_node_id == self.to_node_id
        ):
            raise ValueError("self lineage edges are not allowed")


@dataclass(frozen=True, slots=True)
class ResearchContradictionRecord:
    contradiction_id: str
    contradiction_type: str
    resolution_status: str
    confidence: float
    claim_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.contradiction_id.strip():
            raise ValueError("contradiction_id is required")
        if len(set(self.claim_ids)) < 2:
            raise ValueError("contradiction requires at least two claim ids")
        if self.contradiction_type not in _ALLOWED_CONTRADICTION_TYPES:
            raise ValueError("unsupported contradiction_type")
        if self.resolution_status not in _ALLOWED_RESOLUTION_STATES:
            raise ValueError("unsupported resolution_status")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")


@dataclass(frozen=True, slots=True)
class ResearchSearchAttemptRecord:
    attempt_id: str
    query: str
    engine: str
    result_count: int
    status: str
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.attempt_id.strip():
            raise ValueError("attempt_id is required")
        if not self.query.strip():
            raise ValueError("query is required")
        if self.result_count < 0:
            raise ValueError("result_count must be non-negative")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")


@dataclass(frozen=True, slots=True)
class ResearchCoverageMetricRecord:
    metric_id: str
    dimension: str
    coverage_fraction: float | None
    scoped: bool = True

    def __post_init__(self) -> None:
        if not self.metric_id.strip():
            raise ValueError("metric_id is required")
        if not self.dimension.strip():
            raise ValueError("dimension is required")
        if (
            self.coverage_fraction is not None
            and not 0.0 <= self.coverage_fraction <= 1.0
        ):
            raise ValueError("coverage_fraction must be within 0..1")


@dataclass(frozen=True, slots=True)
class ResearchArtifactRecord:
    tenant_id: str
    artifact_id: str
    decision: str
    truth_state: str
    ready_for_analysis: bool
    scope: dict[str, Any]
    gaps: tuple[dict[str, Any], ...]
    source_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    lineage_edges: tuple[ResearchLineageEdgeRecord, ...] = ()
    contradictions: tuple[ResearchContradictionRecord, ...] = ()
    search_attempts: tuple[ResearchSearchAttemptRecord, ...] = ()
    coverage_metrics: tuple[ResearchCoverageMetricRecord, ...] = ()

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not self.artifact_id.strip():
            raise ValueError("artifact_id is required")
        if self.decision not in _ALLOWED_DECISIONS:
            raise ValueError("unsupported research decision")
        if self.truth_state == "VERIFIED":
            raise PermissionError(
                "research persistence cannot persist VERIFIED authority state"
            )
        if self.truth_state not in _ALLOWED_TRUTH_STATES:
            raise ValueError("unsupported research truth_state")


class ResearchRepository(Protocol):
    async def store_artifact(self, artifact: ResearchArtifactRecord) -> bool: ...

    async def load_artifact(
        self,
        *,
        tenant_id: str,
        artifact_id: str,
    ) -> ResearchArtifactRecord: ...


class PostgresResearchRepository:
    """PostgreSQL persistence for research artifacts.

    The repository is an append-only storage boundary. It validates tenant-
    scoped source and claim references before persisting an artifact, but it
    cannot grant VERIFIED state or approve research output.
    """

    def __init__(self, pool: Any, runtime_config: RuntimeBindingConfig) -> None:
        self._pool = pool
        self._runtime_config = runtime_config

    @classmethod
    async def from_runtime_binding(
        cls,
        runtime_config: RuntimeBindingConfig | None = None,
    ) -> PostgresResearchRepository:
        cfg = runtime_config or RuntimeBindingConfig.from_env()
        pool = await get_db_pool(cfg)
        return cls(pool, cfg)

    async def verify_schema(self) -> None:
        required = (
            "knowledge_research_artifacts",
            "knowledge_research_artifact_sources",
            "knowledge_research_artifact_claims",
            "knowledge_research_lineage_edges",
            "knowledge_research_contradictions",
            "knowledge_research_search_attempts",
            "knowledge_research_coverage_metrics",
        )
        async with acquire_db_connection(
            self._pool,
            self._runtime_config,
        ) as conn:
            missing: list[str] = []
            for table in required:
                exists = await conn.fetchval(
                    "SELECT to_regclass($1)",
                    f"public.{table}",
                )
                if exists is None:
                    missing.append(table)
        if missing:
            raise RuntimeError(
                "research persistence schema missing: "
                + ", ".join(missing)
            )

    async def store_artifact(
        self,
        artifact: ResearchArtifactRecord,
    ) -> bool:
        artifact_payload = _json_payload(artifact)
        async with acquire_db_connection(
            self._pool,
            self._runtime_config,
        ) as conn, conn.transaction():
            existing = await conn.fetchrow(
                """
                    SELECT payload
                    FROM knowledge_research_artifacts
                    WHERE tenant_id = $1 AND artifact_id = $2
                    FOR UPDATE
                    """,
                artifact.tenant_id,
                artifact.artifact_id,
            )
            if existing is not None:
                if _payload_dict(existing["payload"]) == json.loads(
                    artifact_payload
                ):
                    return False
                raise ValueError(
                    "artifact_id already exists with different payload"
                )

            await self._validate_references(conn, artifact)

            await conn.execute(
                """
                    INSERT INTO knowledge_research_artifacts (
                        tenant_id,
                        artifact_id,
                        decision,
                        truth_state,
                        ready_for_analysis,
                        scope_json,
                        gaps_json,
                        payload
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6::jsonb,
                        $7::jsonb,
                        $8::jsonb
                    )
                    """,
                artifact.tenant_id,
                artifact.artifact_id,
                artifact.decision,
                artifact.truth_state,
                artifact.ready_for_analysis,
                json.dumps(artifact.scope, sort_keys=True),
                json.dumps(list(artifact.gaps), sort_keys=True),
                artifact_payload,
            )

            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_artifact_sources (
                        tenant_id,
                        artifact_id,
                        source_id
                    )
                    VALUES ($1, $2, $3)
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        source_id,
                    )
                    for source_id in artifact.source_ids
                ],
            )
            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_artifact_claims (
                        tenant_id,
                        artifact_id,
                        claim_id
                    )
                    VALUES ($1, $2, $3)
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        claim_id,
                    )
                    for claim_id in artifact.claim_ids
                ],
            )
            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_lineage_edges (
                        tenant_id,
                        artifact_id,
                        edge_id,
                        from_node_kind,
                        from_node_id,
                        to_node_kind,
                        to_node_id,
                        edge_type,
                        independent_validation,
                        payload
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7,
                        $8,
                        $9,
                        $10::jsonb
                    )
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        edge.edge_id,
                        edge.from_node_kind,
                        edge.from_node_id,
                        edge.to_node_kind,
                        edge.to_node_id,
                        edge.edge_type,
                        edge.independent_validation,
                        _json_payload(edge),
                    )
                    for edge in artifact.lineage_edges
                ],
            )
            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_contradictions (
                        tenant_id,
                        artifact_id,
                        contradiction_id,
                        contradiction_type,
                        resolution_status,
                        confidence,
                        claim_ids,
                        payload
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7::jsonb,
                        $8::jsonb
                    )
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        item.contradiction_id,
                        item.contradiction_type,
                        item.resolution_status,
                        item.confidence,
                        json.dumps(list(item.claim_ids)),
                        _json_payload(item),
                    )
                    for item in artifact.contradictions
                ],
            )
            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_search_attempts (
                        tenant_id,
                        artifact_id,
                        attempt_id,
                        query,
                        engine,
                        result_count,
                        duration_ms,
                        status,
                        payload
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7,
                        $8,
                        $9::jsonb
                    )
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        item.attempt_id,
                        item.query,
                        item.engine,
                        item.result_count,
                        item.duration_ms,
                        item.status,
                        _json_payload(item),
                    )
                    for item in artifact.search_attempts
                ],
            )
            await _insert_many(
                conn,
                """
                    INSERT INTO knowledge_research_coverage_metrics (
                        tenant_id,
                        artifact_id,
                        metric_id,
                        dimension,
                        coverage_fraction,
                        scoped,
                        payload
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7::jsonb
                    )
                    """,
                [
                    (
                        artifact.tenant_id,
                        artifact.artifact_id,
                        item.metric_id,
                        item.dimension,
                        item.coverage_fraction,
                        item.scoped,
                        _json_payload(item),
                    )
                    for item in artifact.coverage_metrics
                ],
            )
        return True

    async def load_artifact(
        self,
        *,
        tenant_id: str,
        artifact_id: str,
    ) -> ResearchArtifactRecord:
        if not tenant_id.strip() or not artifact_id.strip():
            raise ValueError("tenant_id and artifact_id are required")

        async with acquire_db_connection(
            self._pool,
            self._runtime_config,
        ) as conn:
            row = await conn.fetchrow(
                """
                SELECT payload
                FROM knowledge_research_artifacts
                WHERE tenant_id = $1 AND artifact_id = $2
                """,
                tenant_id,
                artifact_id,
            )

        if row is None:
            raise KeyError("unknown research artifact for tenant")

        return _artifact_from_payload(row["payload"])

    async def _validate_references(
        self,
        conn: Any,
        artifact: ResearchArtifactRecord,
    ) -> None:
        if artifact.source_ids:
            rows = await conn.fetch(
                """
                SELECT source_id
                FROM knowledge_sources
                WHERE tenant_id = $1 AND source_id = ANY($2::text[])
                FOR SHARE
                """,
                artifact.tenant_id,
                list(artifact.source_ids),
            )
            found = {str(row["source_id"]) for row in rows}
            missing = sorted(set(artifact.source_ids) - found)
            if missing:
                raise ValueError(
                    "unknown research source ids for tenant: "
                    + ", ".join(missing)
                )

        if artifact.claim_ids:
            rows = await conn.fetch(
                """
                SELECT claim_id
                FROM knowledge_claims
                WHERE tenant_id = $1 AND claim_id = ANY($2::text[])
                FOR SHARE
                """,
                artifact.tenant_id,
                list(artifact.claim_ids),
            )
            found = {str(row["claim_id"]) for row in rows}
            missing = sorted(set(artifact.claim_ids) - found)
            if missing:
                raise ValueError(
                    "unknown research claim ids for tenant: "
                    + ", ".join(missing)
                )

        source_ids = set(artifact.source_ids)
        claim_ids = set(artifact.claim_ids)

        def node_known(kind: str, node_id: str) -> bool:
            if kind == "SOURCE":
                return node_id in source_ids
            return node_id in claim_ids

        for edge in artifact.lineage_edges:
            if not node_known(edge.from_node_kind, edge.from_node_id):
                raise ValueError(
                    "lineage edge references unknown from node"
                )
            if not node_known(edge.to_node_kind, edge.to_node_id):
                raise ValueError(
                    "lineage edge references unknown to node"
                )

        for item in artifact.contradictions:
            unknown = sorted(set(item.claim_ids) - claim_ids)
            if unknown:
                raise ValueError(
                    "contradiction references unknown claim ids: "
                    + ", ".join(unknown)
                )


async def _insert_many(
    conn: Any,
    sql: str,
    rows: list[tuple[Any, ...]],
) -> None:
    if rows:
        await conn.executemany(sql, rows)


def _json_payload(value: Any) -> str:
    return json.dumps(
        asdict(value),
        sort_keys=True,
        separators=(",", ":"),
    )


def _payload_dict(value: Any) -> dict[str, Any]:
    loaded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(loaded, dict):
        raise ValueError("research persistence payload must be an object")
    return dict(loaded)


def _artifact_from_payload(value: Any) -> ResearchArtifactRecord:
    payload = _payload_dict(value)
    return ResearchArtifactRecord(
        tenant_id=str(payload["tenant_id"]),
        artifact_id=str(payload["artifact_id"]),
        decision=str(payload["decision"]),
        truth_state=str(payload["truth_state"]),
        ready_for_analysis=bool(payload["ready_for_analysis"]),
        scope=dict(payload.get("scope", {})),
        gaps=tuple(payload.get("gaps", ())),
        source_ids=tuple(payload.get("source_ids", ())),
        claim_ids=tuple(payload.get("claim_ids", ())),
        lineage_edges=tuple(
            ResearchLineageEdgeRecord(**item)
            for item in payload.get("lineage_edges", ())
        ),
        contradictions=tuple(
            ResearchContradictionRecord(
                contradiction_id=str(item["contradiction_id"]),
                contradiction_type=str(item["contradiction_type"]),
                resolution_status=str(item["resolution_status"]),
                confidence=float(item["confidence"]),
                claim_ids=tuple(item.get("claim_ids", ())),
            )
            for item in payload.get("contradictions", ())
        ),
        search_attempts=tuple(
            ResearchSearchAttemptRecord(**item)
            for item in payload.get("search_attempts", ())
        ),
        coverage_metrics=tuple(
            ResearchCoverageMetricRecord(**item)
            for item in payload.get("coverage_metrics", ())
        ),
    )

[executed on device: 10616a96dd5c121bb (99b698de-7e79-4f9c-ad45-281a8377dada)]