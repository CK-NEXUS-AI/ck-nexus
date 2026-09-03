# Knowledge Lexical Retrieval V1

Status: IMPLEMENTED_NOT_VERIFIED

## Goal

Add the smallest deterministic retrieval baseline after Knowledge Persistence V2
without introducing a vector database or a second persistence stack.

## Design

- PostgreSQL built-in full-text search only.
- `websearch_to_tsquery('simple', ...)` for bounded user query parsing.
- GIN expression index over claim subject, predicate, and persisted claim value.
- Tenant filter is mandatory.
- Claims with no active source are excluded before ranking.
- Expired `fresh_until` claims are excluded before ranking.
- Ranking uses `ts_rank_cd`, then `observed_at DESC`, then `claim_id ASC`.
- Returned source references contain only active source IDs.
- Query length is capped at 512 characters.
- Result limit is capped at 100.

## Governance Boundary

This is Development evidence only. Ranking does not alter verification state,
governance authority, Q10/Q11/Q12, or Production readiness.

## Adoption Gates

Before canonical adoption:
1. unit and security CI,
2. live PostgreSQL migration + retrieval round trip,
3. query-plan/index-use check,
4. benchmark against the persistence baseline,
5. security review,
6. independent verification and human review.

Vector/semantic retrieval remains deferred until this lexical baseline is
benchmarked.
