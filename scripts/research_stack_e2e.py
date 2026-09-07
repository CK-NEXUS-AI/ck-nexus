"""Staging-only end-to-end verification for the integrated research stack.

The harness proves live SearXNG discovery -> deterministic research compilation
-> PostgreSQL persistence across separate processes. It creates no claims from
search snippets, grants no verification authority, and is not a Production path.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

from creator_app.global_knowledge.connectors.searxng import (
    SearchHit,
    SearxngConfig,
    SearxngDiscoveryAdapter,
    SearxngStatus,
)
from creator_app.global_knowledge.contracts import SourceKind, SourceRef
from creator_app.global_knowledge.research_intelligence import (
    ResearchRequirements,
    SourceObservation,
    compile_research_artifact,
    decide_research_cycle,
)
from creator_app.global_knowledge.research_persistence_bridge import (
    artifact_to_record,
    source_ref_to_record,
)
from creator_app.runtime_binding import RuntimeBindingConfig
from idea_engine.knowledge_repository import PostgresKnowledgeRepository
from idea_engine.research_repository import (
    PostgresResearchRepository,
    ResearchSearchAttemptRecord,
)


def source_from_hit(hit: SearchHit, *, observed_at: str) -> SourceRef:
    payload = json.dumps(
        {
            "url": hit.url,
            "title": hit.title,
            "snippet": hit.snippet,
            "engine": hit.engine,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return SourceRef(
        source_id=f"searxng-{digest[:24]}",
        url=hit.url,
        canonical_url=hit.url,
        source_kind=SourceKind.PUBLIC_DOCUMENT,
        language="und",
        region="unknown",
        observed_at=observed_at,
        content_hash=digest,
        title=hit.title or hit.url,
        metadata={
            "discovery_only": True,
            "engine": hit.engine or "unknown",
        },
    )


def lineage_id_for_source(source: SourceRef) -> str:
    hostname = (urlsplit(source.canonical_url).hostname or "").lower()
    return f"host:{hostname}"


def compile_discovery(
    hits: tuple[SearchHit, ...],
    *,
    observed_at: str,
):
    sources = tuple(source_from_hit(hit, observed_at=observed_at) for hit in hits)
    observations = tuple(
        SourceObservation(
            source=source,
            lineage_id=lineage_id_for_source(source),
        )
        for source in sources
    )
    artifact = compile_research_artifact(
        observations,
        (),
        ResearchRequirements(
            min_sources=3,
            min_independent_lineages=2,
            min_primary_sources=0,
        ),
    )
    decision = decide_research_cycle(artifact)
    return sources, artifact, decision


async def open_repositories(database_url: str):
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("asyncpg is required for research stack E2E") from exc

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
    return (
        pool,
        PostgresKnowledgeRepository(pool, config),
        PostgresResearchRepository(pool, config),
    )


async def write_phase(args: argparse.Namespace) -> int:
    observed_at = datetime.now(UTC).isoformat()
    adapter = SearxngDiscoveryAdapter(
        SearxngConfig(
            base_url=args.searxng_url,
            timeout_seconds=10,
            max_results=8,
            safe_search=1,
        )
    )
    started = monotonic()
    result = await adapter.search(args.query)
    duration_ms = round((monotonic() - started) * 1000)
    if result.status is not SearxngStatus.SUCCESS:
        raise RuntimeError(f"SearXNG discovery failed safely: {result.reason}")
    if not result.hits:
        raise RuntimeError("SearXNG discovery returned no admissible public URLs")

    sources, artifact, decision = compile_discovery(
        result.hits,
        observed_at=observed_at,
    )
    tenant_id = f"research-e2e-{args.run_id}"
    artifact_id = f"artifact-{args.run_id}"

    state = {
        "version": 1,
        "tenant_id": tenant_id,
        "artifact_id": artifact_id,
        "source_ids": list(artifact.source_ids),
        "claim_ids": [],
        "decision": decision.action.name,
        "truth_state": "MEASURED_NOT_VERIFIED",
        "ready_for_analysis": artifact.ready_for_analysis,
        "verified": artifact.verified,
        "search_result_count": len(result.hits),
        "observed_at": observed_at,
        "subject_sha": os.getenv("GITHUB_SHA", "local"),
    }
    Path(args.state_file).write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pool, knowledge_repo, research_repo = await open_repositories(args.database_url)
    try:
        await knowledge_repo.verify_schema()
        await research_repo.verify_schema()

        for source in sources:
            await knowledge_repo.store_source(
                source_ref_to_record(
                    source,
                    tenant_id=tenant_id,
                    trust_score=0.0,
                )
            )

        record = artifact_to_record(
            artifact,
            decision,
            tenant_id=tenant_id,
            artifact_id=artifact_id,
            scope={
                "query": args.query,
                "discovery_only": True,
                "trust_policy": "untrusted_until_independently_admitted",
            },
            claims=(),
        )
        record = replace(
            record,
            search_attempts=(
                ResearchSearchAttemptRecord(
                    attempt_id=f"attempt-{args.run_id}",
                    query=args.query,
                    engine="searxng",
                    result_count=len(result.hits),
                    duration_ms=duration_ms,
                    status="SUCCESS",
                ),
            ),
        )
        if record.truth_state == "VERIFIED":
            raise PermissionError("E2E harness cannot produce VERIFIED state")

        await research_repo.store_artifact(record)
        loaded = await research_repo.load_artifact(
            tenant_id=tenant_id,
            artifact_id=artifact_id,
        )
        if loaded != record:
            raise AssertionError("research artifact round-trip mismatch")
    finally:
        await pool.close()

    state["truth_state"] = record.truth_state
    Path(args.state_file).write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"phase": "write", **state}, sort_keys=True))
    return 0


async def verify_phase(args: argparse.Namespace) -> int:
    state = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
    pool, knowledge_repo, research_repo = await open_repositories(args.database_url)
    try:
        await knowledge_repo.verify_schema()
        await research_repo.verify_schema()
        loaded = await research_repo.load_artifact(
            tenant_id=state["tenant_id"],
            artifact_id=state["artifact_id"],
        )
        sources, claims, _revoked = await knowledge_repo.load_tenant(
            state["tenant_id"]
        )
    finally:
        await pool.close()

    if loaded.truth_state == "VERIFIED":
        raise PermissionError("persisted research artifact unexpectedly VERIFIED")
    if tuple(state["source_ids"]) != loaded.source_ids:
        raise AssertionError("persisted source identity mismatch")
    if len(sources) != len(state["source_ids"]):
        raise AssertionError("persisted source count mismatch")
    if claims:
        raise AssertionError("discovery-only E2E must not synthesize claims")

    result = {
        "phase": "verify",
        "tenant_id": state["tenant_id"],
        "artifact_id": state["artifact_id"],
        "source_count": len(sources),
        "claim_count": len(claims),
        "decision": loaded.decision,
        "truth_state": loaded.truth_state,
        "ready_for_analysis": loaded.ready_for_analysis,
        "verified_authority": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


async def cleanup_phase(args: argparse.Namespace) -> int:
    state = json.loads(Path(args.state_file).read_text(encoding="utf-8"))
    pool, _knowledge_repo, _research_repo = await open_repositories(args.database_url)
    try:
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "DELETE FROM knowledge_research_artifacts WHERE tenant_id = $1",
                state["tenant_id"],
            )
            await conn.execute(
                "DELETE FROM knowledge_claims WHERE tenant_id = $1",
                state["tenant_id"],
            )
            await conn.execute(
                "DELETE FROM knowledge_sources WHERE tenant_id = $1",
                state["tenant_id"],
            )
            remaining = await conn.fetchval(
                "SELECT count(*) FROM knowledge_sources WHERE tenant_id = $1",
                state["tenant_id"],
            )
    finally:
        await pool.close()

    if remaining:
        raise AssertionError("research E2E cleanup leaked tenant sources")
    print(
        json.dumps(
            {
                "phase": "cleanup",
                "tenant_id": state["tenant_id"],
                "remaining_sources": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("write", "verify", "cleanup"), required=True)
    parser.add_argument(
        "--database-url",
        default=os.getenv("CK_KNOWLEDGE_PG_TEST_URL", "").strip(),
    )
    parser.add_argument(
        "--searxng-url",
        default=os.getenv("CKNEXUS_SEARXNG_URL", "http://127.0.0.1:8080/"),
    )
    parser.add_argument("--query", default="Python programming language")
    parser.add_argument(
        "--run-id",
        default=os.getenv("GITHUB_RUN_ID", "local"),
    )
    parser.add_argument(
        "--state-file",
        default="/tmp/cknexus-research-stack-e2e.json",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or CK_KNOWLEDGE_PG_TEST_URL is required")
    return args


async def amain() -> int:
    args = parse_args()
    if args.phase == "write":
        return await write_phase(args)
    if args.phase == "verify":
        return await verify_phase(args)
    return await cleanup_phase(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain()))
