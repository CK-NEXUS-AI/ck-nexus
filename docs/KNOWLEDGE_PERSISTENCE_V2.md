# CK-NEXUS Knowledge Persistence V2

Status: DEVELOPMENT ONLY / IMPLEMENTED_NOT_VERIFIED

This work package is stacked on Cognitive Knowledge Fabric V1 and does not modify the frozen Q10 subject, release authority, or Production state.

## Purpose

Knowledge Persistence V2 adds a PostgreSQL persistence boundary for Knowledge Fabric records without introducing a second database stack. It reuses the canonical CK-NEXUS PostgreSQL runtime binding in `creator_app/runtime_binding.py` and keeps retrieval ranking, knowledge confidence, memory proposals, and release verification as separate authorities.

## Reused baseline

The implementation deliberately reuses:

- `RuntimeBindingConfig`
- `get_db_pool()`
- `acquire_db_connection()`
- existing `SourceRecord`, `KnowledgeClaim`, and `MemoryWriteProposal` contracts
- the existing rule that changed source content requires a new source identity rather than overwriting prior history
- tenant-scoped provenance and relationship semantics from the earlier knowledge/memory architecture work

It does not add a vector database, graph database, new connection manager, or new release-verification authority.

## PostgreSQL schema

Migration:

`migrations/postgresql/004_knowledge_fabric_v2.sql`

Tables:

- `knowledge_sources`
- `knowledge_claims`
- `knowledge_claim_sources`
- `knowledge_claim_relations`
- `knowledge_memory_proposals`
- `knowledge_memory_proposal_claims`

Every knowledge identity and foreign-key relationship carries `tenant_id`. Cross-tenant source/claim relationships are therefore rejected both by the runtime repository and by composite database foreign keys.

## Transaction boundaries

Source creation, claim creation with provenance/relations, and memory-proposal creation execute inside explicit PostgreSQL transactions. A failed provenance or relationship check must roll back the full operation rather than leave partial rows.

Source revocation is tenant-scoped and does not delete provenance history. Revocation changes retrieval eligibility in the Knowledge Fabric layer; it is not a deletion or verification action.

## Source identity and versioning

`source_id` remains the stable knowledge-source identity. `source_hash` binds content identity. The current V1 compatibility contract carries an optional source version in:

`SourceRecord.metadata["source_version"]`

This avoids changing the V1 dataclass contract inside the persistence PR. A future schema revision may promote `source_version` to a first-class field only after compatibility review and benchmark evidence.

Re-ingestion of an identical persisted payload is idempotent. A changed source under the same `(tenant_id, source_id)` fails closed rather than silently overwriting history.

## Memory boundary

The repository stores only `MemoryWriteProposal` records. It does not approve or activate them. Any proposal marked `auto_approved=True` is rejected by the repository.

Knowledge Persistence V2 therefore cannot:

- approve itself
- alter release gates
- alter policy
- mutate credentials
- mark a governance claim VERIFIED
- deploy to Production

## Verification levels

Unit tests use fake connections to verify transaction and tenant boundaries without claiming a live PostgreSQL integration pass.

The opt-in integration test is:

`tests/integration/test_knowledge_persistence_postgres.py`

It runs only when `CK_KNOWLEDGE_PG_TEST_URL` is explicitly configured. A skipped integration test is not evidence that PostgreSQL persistence works in a real environment.

Before adoption, the following are still required:

1. Compile/Ruff pass
2. Bandit and secret-scan pass
3. portable regression pass
4. live PostgreSQL integration test against the migration
5. rollback/failure-path verification
6. security review
7. independent verification
8. human PR review

## Relationship to Q10

This branch is a Development Lane candidate only. Its CI output, test database, and GitHub Actions runtime must not be used as canonical Q10 evidence for frozen commit `39f5c1adb9d761ab418cf088ff1f051b1ca731d1` and tree `0525195934f703a8becf8a39f6397b2411e0bb2e`.

Q10 remains NOT_VERIFIED until its separate exact-subject evidence, Darker verification, independent human review, and owner human sign-off are complete.
