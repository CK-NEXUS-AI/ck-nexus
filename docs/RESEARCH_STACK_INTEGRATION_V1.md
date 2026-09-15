# CK-NEXUS Research Stack Integration V1

Status: Post-P0 development integration candidate.

Base lane: PR #244 SearXNG Development Runtime V1.

Integrated dependencies:
- PR #242 knowledge-driven research contracts and decision logic
- PR #243 PostgreSQL knowledge and research persistence
- PR #244 SearXNG development runtime

## Purpose

This integration tree proves that the research intelligence, persistence, and
self-hosted discovery runtime can coexist in one exact development tree.

It does not merge or close the source pull requests.

## Integration boundary

The tree adds the minimum persistence dependency closure required by the
research stack:

- idea_engine/knowledge_fabric.py
- idea_engine/knowledge_repository.py
- idea_engine/research_repository.py
- migrations/postgresql/004_knowledge_fabric_v2.sql
- migrations/postgresql/005_research_artifacts_v1.sql

It does not import branch-specific historical workflow files from PR #216 or
PR #243.

## Research persistence bridge

The canonical bridge is:

creator_app/global_knowledge/research_persistence_bridge.py

It translates:

- SourceRef into SourceRecord
- Claim into KnowledgeClaim
- ResearchCompilationArtifact into ResearchArtifactRecord

The bridge has no verification authority.

Rules:
- trust_score must be supplied explicitly
- claims remain OBSERVED when converted
- artifact claim IDs must exactly match supplied claims
- claim source IDs must belong to the research artifact
- worker artifacts marked VERIFIED are rejected
- persistence truth state is at most MEASURED_NOT_VERIFIED or REVIEW_REQUIRED

## Validation

Dedicated workflow:

.github/workflows/research-stack-integration-20260907.yml

The workflow validates one exact SHA by running:

1. research and discovery contract tests
2. knowledge persistence unit tests
3. research persistence unit tests
4. bridge invariant tests
5. PostgreSQL migration 004
6. PostgreSQL migration 005
7. live PostgreSQL round-trip tests
8. migration idempotency
9. SearXNG Compose validation
10. live SearXNG JSON readiness
11. runtime teardown

## Authority boundary

Successful development integration establishes measured compatibility only.

It does not establish:
- independent verification
- owner sign-off
- Q10/Q11/Q12 completion
- Production readiness
- certification
- permission for a worker to approve itself

The expected status after successful automated validation remains
MEASURED_NOT_VERIFIED.
