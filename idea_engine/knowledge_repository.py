[Reading 494 lines from start (total: 494 lines, 0 remaining)]

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Protocol

from creator_app.runtime_binding import (
    RuntimeBindingConfig,
    acquire_db_connection,
    get_db_pool,
)

from .knowledge_fabric import (
    CanonicalSourceKind,
    ClaimClass,
    KnowledgeClaim,
    MemoryWriteProposal,
    SourceClass,
    SourceRecord,
    VerificationState,
)


class KnowledgeRepository(Protocol):
    async def store_source(self, source: SourceRecord) -> bool: ...

    async def store_claim(self, claim: KnowledgeClaim) -> None: ...

    async def set_source_revoked(
        self,
        *,
        tenant_id: str,
        source_id: str,
        revoked: bool,
    ) -> None: ...

    async def load_tenant(
        self,
        tenant_id: str,
    ) -> tuple[tuple[SourceRecord, ...], tuple[KnowledgeClaim, ...], frozenset[str]]: ...

    async def store_memory_proposal(self, proposal: MemoryWriteProposal) -> None: ...


class PostgresKnowledgeRepository:
    """PostgreSQL persistence for Knowledge Fabric V2.

    The repository reuses CK-NEXUS runtime binding and transaction boundaries.
    It never upgrades a claim's verification state and never approves memory
    proposals. Tenant identity is included in every primary/foreign-key lookup.
    """

    def __init__(self, pool: Any, runtime_config: RuntimeBindingConfig) -> None:
        self._pool = pool
        self._runtime_config = runtime_config

    @classmethod
    async def from_runtime_binding(
        cls,
        runtime_config: RuntimeBindingConfig | None = None,
    ) -> PostgresKnowledgeRepository:
        cfg = runtime_config or RuntimeBindingConfig.from_env()
        pool = await get_db_pool(cfg)
        return cls(pool, cfg)

    async def verify_schema(self) -> None:
        required = (
            "knowledge_sources",
            "knowledge_claims",
            "knowledge_claim_sources",
            "knowledge_claim_relations",
            "knowledge_memory_proposals",
            "knowledge_memory_proposal_claims",
        )
        async with acquire_db_connection(self._pool, self._runtime_config) as conn:
            missing: list[str] = []
            for table in required:
                exists = await conn.fetchval("SELECT to_regclass($1)", f"public.{table}")
                if exists is None:
                    missing.append(table)
        if missing:
            raise RuntimeError("knowledge persistence schema missing: " + ", ".join(missing))

    async def store_source(self, source: SourceRecord) -> bool:
        payload = _json_payload(source)
        source_version = source.metadata.get("source_version")
        async with (
            acquire_db_connection(self._pool, self._runtime_config) as conn,
            conn.transaction(),
        ):
                existing = await conn.fetchrow(
                    """
                    SELECT source_hash, source_version, payload::text AS payload
                    FROM knowledge_sources
                    WHERE tenant_id = $1 AND source_id = $2
                    FOR UPDATE
                    """,
                    source.tenant_id,
                    source.source_id,
                )
                if existing is not None:
                    if _source_matches(existing, source, payload, source_version):
                        return False
                    raise ValueError(
                        "source_id already exists with different content or metadata"
                    )
                await conn.execute(
                    """
                    INSERT INTO knowledge_sources (
                        tenant_id,
                        source_id,
                        source_hash,
                        source_version,
                        payload
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    """,
                    source.tenant_id,
                    source.source_id,
                    source.source_hash,
                    source_version,
                    payload,
                )
        return True

    async def store_claim(self, claim: KnowledgeClaim) -> None:
        payload = _json_payload(claim)
        observed_at = _postgres_timestamp(claim.observed_at)
        fresh_until = _postgres_timestamp(claim.fresh_until)
        async with (
            acquire_db_connection(self._pool, self._runtime_config) as conn,
            conn.transaction(),
        ):
                if await conn.fetchval(
                    """
                    SELECT 1
                    FROM knowledge_claims
                    WHERE tenant_id = $1 AND claim_id = $2
                    """,
                    claim.tenant_id,
                    claim.claim_id,
                ):
                    raise ValueError("claim_id already exists")

                source_rows = await conn.fetch(
                    """
                    SELECT source_id
                    FROM knowledge_sources
                    WHERE tenant_id = $1 AND source_id = ANY($2::text[])
                    FOR SHARE
                    """,
                    claim.tenant_id,
                    list(claim.source_ids),
                )
                found_sources = {str(row["source_id"]) for row in source_rows}
                missing_sources = sorted(set(claim.source_ids) - found_sources)
                if missing_sources:
                    raise ValueError(
                        "unknown source_ids for tenant: " + ", ".join(missing_sources)
                    )

                related_ids = tuple(dict.fromkeys((*claim.contradicts, *claim.supersedes)))
                if related_ids:
                    relation_rows = await conn.fetch(
                        """
                        SELECT claim_id
                        FROM knowledge_claims
                        WHERE tenant_id = $1 AND claim_id = ANY($2::text[])
                        FOR SHARE
                        """,
                        claim.tenant_id,
                        list(related_ids),
                    )
                    found_relations = {str(row["claim_id"]) for row in relation_rows}
                    missing_relations = sorted(set(related_ids) - found_relations)
                    if missing_relations:
                        raise ValueError(
                            "unknown related claim ids for tenant: "
                            + ", ".join(missing_relations)
                        )

                await conn.execute(
                    """
                    INSERT INTO knowledge_claims (
                        tenant_id,
                        claim_id,
                        subject,
                        predicate,
                        claim_class,
                        observed_at,
                        fresh_until,
                        confidence,
                        payload
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::timestamptz, $7::timestamptz, $8, $9::jsonb)
                    """,
                    claim.tenant_id,
                    claim.claim_id,
                    claim.subject,
                    claim.predicate,
                    claim.claim_class.value,
                    observed_at,
                    fresh_until,
                    claim.confidence,
                    payload,
                )
                await conn.executemany(
                    """
                    INSERT INTO knowledge_claim_sources (tenant_id, claim_id, source_id)
                    VALUES ($1, $2, $3)
                    """,
                    [
                        (claim.tenant_id, claim.claim_id, source_id)
                        for source_id in claim.source_ids
                    ],
                )
                relation_rows_to_insert = [
                    (claim.tenant_id, claim.claim_id, "contradicts", related_id)
                    for related_id in claim.contradicts
                ] + [
                    (claim.tenant_id, claim.claim_id, "supersedes", related_id)
                    for related_id in claim.supersedes
                ]
                if relation_rows_to_insert:
                    await conn.executemany(
                        """
                        INSERT INTO knowledge_claim_relations (
                            tenant_id,
                            claim_id,
                            relation_type,
                            related_claim_id
                        )
                        VALUES ($1, $2, $3, $4)
                        """,
                        relation_rows_to_insert,
                    )

    async def set_source_revoked(
        self,
        *,
        tenant_id: str,
        source_id: str,
        revoked: bool,
    ) -> None:
        if not tenant_id.strip() or not source_id.strip():
            raise ValueError("tenant_id and source_id are required")
        async with acquire_db_connection(self._pool, self._runtime_config) as conn:
            result = await conn.execute(
                """
                UPDATE knowledge_sources
                SET revoked = $3, updated_at = now()
                WHERE tenant_id = $1 AND source_id = $2
                """,
                tenant_id,
                source_id,
                revoked,
            )
        if result != "UPDATE 1":
            raise KeyError("unknown source_id for tenant")

    async def load_tenant(
        self,
        tenant_id: str,
    ) -> tuple[tuple[SourceRecord, ...], tuple[KnowledgeClaim, ...], frozenset[str]]:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        async with acquire_db_connection(self._pool, self._runtime_config) as conn:
            source_rows = await conn.fetch(
                """
                SELECT source_id, revoked, payload
                FROM knowledge_sources
                WHERE tenant_id = $1
                ORDER BY source_id
                """,
                tenant_id,
            )
            claim_rows = await conn.fetch(
                """
                SELECT claim_id, payload
                FROM knowledge_claims
                WHERE tenant_id = $1
                ORDER BY claim_id
                """,
                tenant_id,
            )
            source_links = await conn.fetch(
                """
                SELECT claim_id, source_id
                FROM knowledge_claim_sources
                WHERE tenant_id = $1
                ORDER BY claim_id, source_id
                """,
                tenant_id,
            )
            relation_links = await conn.fetch(
                """
                SELECT claim_id, relation_type, related_claim_id
                FROM knowledge_claim_relations
                WHERE tenant_id = $1
                ORDER BY claim_id, relation_type, related_claim_id
                """,
                tenant_id,
            )

        sources = tuple(_source_from_payload(row["payload"]) for row in source_rows)
        revoked_ids = frozenset(
            str(row["source_id"]) for row in source_rows if bool(row["revoked"])
        )
        sources_by_claim: dict[str, list[str]] = defaultdict(list)
        for row in source_links:
            sources_by_claim[str(row["claim_id"])].append(str(row["source_id"]))
        contradicts_by_claim: dict[str, list[str]] = defaultdict(list)
        supersedes_by_claim: dict[str, list[str]] = defaultdict(list)
        for row in relation_links:
            target = (
                contradicts_by_claim
                if str(row["relation_type"]) == "contradicts"
                else supersedes_by_claim
            )
            target[str(row["claim_id"])].append(str(row["related_claim_id"]))

        claims = tuple(
            _claim_from_payload(
                row["payload"],
                source_ids=tuple(sources_by_claim[str(row["claim_id"])]),
                contradicts=tuple(contradicts_by_claim[str(row["claim_id"])]),
                supersedes=tuple(supersedes_by_claim[str(row["claim_id"])]),
            )
            for row in claim_rows
        )
        return sources, claims, revoked_ids

    async def store_memory_proposal(self, proposal: MemoryWriteProposal) -> None:
        if proposal.auto_approved:
            raise PermissionError("knowledge repository cannot persist auto-approved proposal")
        payload = _json_payload(proposal)
        async with (
            acquire_db_connection(self._pool, self._runtime_config) as conn,
            conn.transaction(),
        ):
                claim_rows = await conn.fetch(
                    """
                    SELECT claim_id
                    FROM knowledge_claims
                    WHERE tenant_id = $1 AND claim_id = ANY($2::text[])
                    FOR SHARE
                    """,
                    proposal.tenant_id,
                    list(proposal.source_claim_ids),
                )
                found = {str(row["claim_id"]) for row in claim_rows}
                missing = sorted(set(proposal.source_claim_ids) - found)
                if missing:
                    raise ValueError(
                        "unknown source claim ids for tenant: " + ", ".join(missing)
                    )
                await conn.execute(
                    """
                    INSERT INTO knowledge_memory_proposals (
                        tenant_id,
                        proposal_id,
                        retention_class,
                        retention_days,
                        payload
                    )
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    """,
                    proposal.tenant_id,
                    proposal.proposal_id,
                    proposal.retention_class.value,
                    proposal.retention_days,
                    payload,
                )
                await conn.executemany(
                    """
                    INSERT INTO knowledge_memory_proposal_claims (
                        tenant_id,
                        proposal_id,
                        claim_id
                    )
                    VALUES ($1, $2, $3)
                    """,
                    [
                        (proposal.tenant_id, proposal.proposal_id, claim_id)
                        for claim_id in proposal.source_claim_ids
                    ],
                )


def _json_payload(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if hasattr(item, "value"):
            return item.value
        if isinstance(item, tuple):
            return [normalize(child) for child in item]
        if isinstance(item, dict):
            return {str(key): normalize(child) for key, child in item.items()}
        return item

    return json.dumps(
        normalize(asdict(value)),
        sort_keys=True,
        separators=(",", ":"),
    )


def _payload_dict(value: Any) -> dict[str, Any]:
    loaded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(loaded, dict):
        raise ValueError("knowledge persistence payload must be an object")
    return dict(loaded)


def _source_matches(
    existing: Any,
    source: SourceRecord,
    payload: str,
    source_version: str | None,
) -> bool:
    existing_payload = _payload_dict(existing["payload"])
    if existing_payload == json.loads(payload):
        return True
    existing_hash = existing["source_hash"]
    if source.source_hash and existing_hash == source.source_hash:
        return existing["source_version"] == source_version
    return False


def _source_from_payload(value: Any) -> SourceRecord:
    payload = _payload_dict(value)
    return SourceRecord(
        source_id=str(payload["source_id"]),
        source_class=SourceClass(str(payload["source_class"])),
        locator=str(payload["locator"]),
        title=str(payload["title"]),
        retrieved_at=str(payload["retrieved_at"]),
        trust_score=float(payload["trust_score"]),
        tenant_id=str(payload.get("tenant_id", "default")),
        source_kind=CanonicalSourceKind(str(payload["source_kind"])),
        language=str(payload.get("language", "und")),
        publisher=_optional_str(payload.get("publisher")),
        author=_optional_str(payload.get("author")),
        published_at=_optional_str(payload.get("published_at")),
        rights=str(payload.get("rights", "unknown")),
        source_hash=_optional_str(payload.get("source_hash")),
        producer=str(payload.get("producer", "ck-nexus")),
        producer_version=_optional_str(payload.get("producer_version")),
        transformation_chain=tuple(payload.get("transformation_chain", ())),
        evidence_refs=tuple(payload.get("evidence_refs", ())),
        metadata={str(key): str(item) for key, item in payload.get("metadata", {}).items()},
    )


def _claim_from_payload(
    value: Any,
    *,
    source_ids: tuple[str, ...],
    contradicts: tuple[str, ...],
    supersedes: tuple[str, ...],
) -> KnowledgeClaim:
    payload = _payload_dict(value)
    return KnowledgeClaim(
        claim_id=str(payload["claim_id"]),
        subject=str(payload["subject"]),
        predicate=str(payload["predicate"]),
        value=str(payload["value"]),
        claim_class=ClaimClass(str(payload["claim_class"])),
        source_ids=source_ids,
        confidence=float(payload["confidence"]),
        observed_at=str(payload["observed_at"]),
        tenant_id=str(payload.get("tenant_id", "default")),
        verification=VerificationState(str(payload.get("verification", "observed"))),
        valid_from=_optional_str(payload.get("valid_from")),
        fresh_until=_optional_str(payload.get("fresh_until")),
        contradicts=contradicts,
        supersedes=supersedes,
        evidence_refs=tuple(payload.get("evidence_refs", ())),
        qualifiers={str(key): str(item) for key, item in payload.get("qualifiers", {}).items()},
    )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _postgres_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
