# CK-NEXUS Knowledge Contract Reconciliation - 2026.09

Status: DEVELOPMENT CANDIDATE / NOT VERIFIED / NOT PRODUCTION

## Decision

Cognitive Knowledge Fabric V1 does not replace the earlier knowledge/memory architecture work from
`arch/knowledge-memory-ingestion-v01` at commit
`4017b6de7ef78f4537a03820c8f76a6990f72fa6`.

The earlier contracts are reused as the schema baseline. The new runtime layer adds deterministic
claim-class separation, freshness/source weighting, conflict grouping and a fail-closed memory-write
proposal boundary.

## Reused schemas

The following files are restored without redesigning their core semantics:

- `schemas/knowledge/source-provenance.schema.json`
- `schemas/knowledge/knowledge-claim.schema.json`
- `schemas/knowledge/memory-record.schema.json`
- `contracts/test-vectors/knowledge_ingestion_vectors.json`

Important semantics preserved from the historical design:

- tenant isolation
- stable source reference
- source/content hashes
- producer/tool identity
- transformation chain
- evidence references
- contradiction links
- supersession links
- temporal validity/freshness
- retention classes
- deletion/revocation state
- de-indexing after source revocation
- idempotent unchanged-source re-ingestion

## Runtime additions from V1

The runtime implementation adds concepts that were not explicit in the older schemas:

- FACT / OPINION / INFERENCE / PREDICTION / ASSUMPTION classes
- deterministic normalized subject/predicate conflict grouping
- retrieval ranking signal based on source trust, freshness and claim confidence
- mapping into the existing IdeaGraph model
- memory writes represented as proposals, never self-approved mutations
- protected authority scopes that the learning layer cannot modify

These additions are runtime semantics. They do not silently redefine VERIFIED or release authority.

## Required V2 compatibility work

Before persistence or vector retrieval is added, V2 must reconcile the runtime dataclasses with the
schema vocabulary:

1. add tenant identity to runtime records;
2. map SourceClass to the canonical source_kind taxonomy;
3. persist source/content hash and transformation chain;
4. preserve contradicts/supersedes relationships;
5. model valid_from/fresh_until explicitly;
6. use retention classes rather than an untyped duration alone;
7. implement source-revocation -> retrieval de-index behavior;
8. implement unchanged-content idempotency using content hashes;
9. ensure retrieval filters tenant and policy before semantic ranking;
10. bind cache/index entries to source version and policy state.

## Database decision

No graph or vector database is selected by this reconciliation.

The first persistent baseline should prefer existing PostgreSQL infrastructure where practical.
A vector or graph engine becomes a candidate only when a benchmark demonstrates a real capability or
material quality/performance gain that cannot be achieved adequately with the existing stack.

## Authority boundary

Knowledge quality, source trust, freshness and model confidence are ranking/evaluation signals.
They are not authority to:

- approve a security gate;
- modify policy;
- declare production readiness;
- change credentials;
- promote a development candidate to VERIFIED.

Those actions remain under the existing CK-NEXUS governance and independent-verification model.
