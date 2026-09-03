# Lexical Retrieval Implementation Plan

This plan is for a subsequent development delta after Knowledge Persistence V2.

Implementation target:
- PostgreSQL full-text search baseline using built-in `tsvector` / `tsquery` / GIN.
- tenant/freshness/revocation eligibility filters before ranking.
- deterministic score and tie-break ordering.
- source references returned with hits.
- no vector database dependency.
- live PostgreSQL tests and benchmark before measured status.
