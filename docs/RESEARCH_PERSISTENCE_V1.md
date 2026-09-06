# CK-NEXUS Research Persistence V1

Status: Post-P0 development candidate.
Base: Knowledge Persistence V2.
Production effect: none.
Verification authority: none.

## Purpose

Research Persistence V1 stores durable research artifacts produced by the
knowledge-driven research layer without introducing a second database stack.

It reuses:

- CK-NEXUS PostgreSQL runtime binding,
- Knowledge Persistence V2 source and claim identities,
- tenant-scoped transaction boundaries,
- append-only identity semantics,
- development evidence boundaries.

## Design decision

The repository does not implement `mark_verified()`.

Storage is not verification authority. The highest accepted stored truth state
is `MEASURED_NOT_VERIFIED`. A separate verification and human-review path must
supply VERIFIED authority when required.

## Migration

Migration:

`migrations/postgresql/005_research_artifacts_v1.sql`

Tables:

- `knowledge_research_artifacts`
- `knowledge_research_artifact_sources`
- `knowledge_research_artifact_claims`
- `knowledge_research_lineage_edges`
- `knowledge_research_contradictions`
- `knowledge_research_search_attempts`
- `knowledge_research_coverage_metrics`

The source and claim association tables reference the canonical
`knowledge_sources` and `knowledge_claims` tables from migration 004 instead
of duplicating source or claim storage.

## Repository

`idea_engine/research_repository.py`

The repository:

- verifies all required research tables,
- rejects unknown tenant-scoped source IDs,
- rejects unknown tenant-scoped claim IDs,
- rejects lineage edges whose endpoints are outside the artifact,
- rejects contradiction records with unknown claims,
- treats exact repeated artifact payloads as idempotent,
- rejects changed payloads under the same artifact identity,
- reconstructs an exact stored artifact payload,
- cannot persist VERIFIED state.

## Live PostgreSQL validation

Workflow:

`.github/workflows/research-persistence-postgres-integration-20260907.yml`

The workflow:

1. verifies the checkout equals the workflow SHA,
2. installs the frozen development environment,
3. runs research persistence unit tests,
4. applies Knowledge Persistence V2 migration 004,
5. applies Research Persistence V1 migration 005,
6. runs a live PostgreSQL round-trip,
7. re-applies both migrations to prove idempotency,
8. checks schema objects and integration-row cleanup.

This is development validation only.

## Relationship to PR #242

PR #242 defines research-domain contracts and decision logic.
This persistence package deliberately does not import PR #242 contracts because
the two development branches are not yet reconciled into one canonical stack.

The future integration bridge should map a
`ResearchCompilationArtifact` into `ResearchArtifactRecord` after both
dependency lanes are adopted. That bridge should remain small and should not
duplicate storage logic.

## Verification boundary

Passing unit tests and live PostgreSQL integration may establish measured
persistence behavior for an exact development SHA.

It does not establish:

- independent verification,
- owner sign-off,
- Q10/Q11/Q12 completion,
- Production readiness,
- VERIFIED status for research claims.
