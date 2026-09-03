# Knowledge Lexical Retrieval Baseline

Status: `DESIGN_STAGING / DEVELOPMENT_ONLY`

This document stages the next delta after Knowledge Persistence V2. It does not activate retrieval behavior and does not change Q10 or Production state.

Constraints:
- PostgreSQL-first; no vector database dependency.
- Tenant filter before ranking.
- Revoked-source exclusion before ranking.
- Freshness filter before ranking.
- Deterministic ranking/tie-breaking.
- Source references returned with every hit.
- Ranking never upgrades verification state.
- Live PostgreSQL test and benchmark required before `MEASURED_NOT_VERIFIED`.
- Semantic/vector retrieval is benchmarked only after this lexical baseline exists.
