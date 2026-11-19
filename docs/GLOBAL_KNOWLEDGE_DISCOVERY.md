# CK-NEXUS Global Knowledge Discovery & Connection System

Status: feature scaffold on a non-production branch. This document does not
change Q10/Q11/Q12 or Production verification state.

## Mission

Turn global, multilingual, fragmented information into evidence-backed,
structured knowledge. CK-NEXUS should answer complex questions by showing not
only an answer, but also the entities, relationships, source lineage,
freshness, uncertainty, and conflicting evidence behind it.

## Core architecture

1. Discovery Orchestrator
   - Broad discovery across languages, regions, and source classes.
   - Deep domain discovery after quality and policy qualification.
   - Reactive search for user questions.
   - Scheduled refresh according to source volatility and value.

2. Connector and Crawl Fabric
   - Search APIs, public feeds, sitemaps, RSS/Atom, public datasets, document
     fetchers, and site-specific adapters.
   - Every adapter runs behind authorization, rate-limit, robots, terms,
     jurisdiction, privacy, and audit gates.
   - No CAPTCHA bypass, credential scraping, paywall bypass, or hidden-data
     collection.

3. Normalization Pipeline
   - MIME/type detection.
   - Text and metadata extraction.
   - Language identification and original-language preservation.
   - Canonical URL normalization.
   - Content hashing and duplicate/near-duplicate detection.
   - Timestamp normalization with separate published_at and observed_at.

4. Provenance Ledger
   - Every ingested object receives a source_id and content hash.
   - Every claim and relationship references one or more source_ids.
   - Preserve original evidence even when normalized representations change.
   - Keep append-only change history for claim revisions and retractions.

5. Entity and Relation Layer
   - Named-entity extraction.
   - Entity resolution using aliases, external IDs, geography, time, and
     contextual evidence.
   - Typed relations such as located_in, employed_by, acquired, caused,
     supports, contradicts, part_of, and influenced_by.
   - Never present inferred relations as observed facts.

6. Knowledge Graph
   - Nodes: people, organizations, places, products, events, concepts,
     datasets, policies, publications.
   - Edges: typed relations with confidence, temporal validity, and provenance.
   - Hyperedge/event representation should be used when a fact depends on more
     than two entities.

7. Search and Retrieval
   - Lexical/full-text retrieval for exact names, numbers, quotes, and terms.
   - Semantic/vector retrieval for conceptual similarity.
   - Hybrid ranking combines both and adds source quality, freshness, region,
     language, and evidence density.
   - Graph traversal adds relationship-aware retrieval.

8. Evidence-backed Answer Engine
   - Query decomposition.
   - Retrieve documents, entities, graph neighborhoods, and contradictory
     evidence.
   - Generate candidate claims.
   - Cross-check claims against independent sources.
   - Return answer + provenance + confidence + freshness + disagreements.

## Trust model

A fact is represented as a claim, not a naked string.

Suggested state progression:

DISCOVERED -> OBSERVED -> CORROBORATED -> VERIFIED

Separate reliability labels must remain visible:

UNKNOWN, USER_PROVIDED, INFERRED, DERIVED, OBSERVED, MEASURED, VERIFIED, STALE

Rules:

- Two sources are not independent merely because they are on two domains.
  Syndicated copies should share an evidence lineage.
- Source reputation is only one input. Claim-level evidence can override
  source-level reputation.
- Confidence should decay when evidence becomes stale for time-sensitive facts.
- Conflicting claims should coexist until resolved; do not overwrite history.
- Original-language evidence is preferred over machine translation for final
  verification.

## Global coverage model

Region packs define preferred languages, source classes, authorities, and
legal/policy profiles without hardcoding political assumptions.

Examples:

- Asia: th, zh, ja, ko, id, vi, hi and others.
- Europe: en, fr, de, es, it, pt, pl, ru and others.
- Americas: en, es, pt, fr and others.
- Africa/Middle East: ar, fr, en, fa, sw and relevant local languages.

The system should measure coverage gaps rather than claiming "all of the
internet". Useful metrics include region coverage, language coverage, source
diversity, freshness, duplication ratio, entity-resolution uncertainty, and
unresolved contradiction count.

## Storage layers

Production target:

- Raw immutable object store for source snapshots.
- Relational/entity store for normalized metadata and resolution state.
- Graph database for entity/relation traversal.
- Hybrid search index for lexical + vector retrieval.
- Cache for expensive query plans and stable answer fragments.
- Evidence ledger for hashes, provenance, policy decisions, and audit events.

The current repository scaffold stays dependency-light and defines contracts,
policy gates, and planning first. Storage engines remain replaceable providers.

## Integration with existing CK-NEXUS components

- ResearcherAgent: user-facing research intent and query decomposition.
- SharedKnowledge: reusable normalized knowledge summaries.
- SemanticMemory: high-value learned context; not a substitute for source
  evidence.
- IdeaGraph: concept/idea relationships; can consume verified entities and
  relations through a later adapter.
- Security/Governance: authority for crawl permissions, sensitive-data rules,
  connector credentials, and dangerous actions.
- Evidence/Verification: authority for claim provenance and verification state.

## Delivery phases

Phase 1: contracts, policy gate, planner, tests.
Phase 2: public web/search connectors and normalized SourceRef ingestion.
Phase 3: deduplication, entity extraction, entity resolution, relation
extraction.
Phase 4: graph store + hybrid index.
Phase 5: evidence-backed complex QA and contradiction handling.
Phase 6: multilingual expansion and region packs.
Phase 7: distributed scheduling, refresh, observability, cost/resource
governance.
Phase 8: independent security/privacy review and production evidence.

## Non-goals

- Mirroring the entire public internet.
- Bypassing access controls or website restrictions.
- Treating generated text as verified evidence.
- Collecting sensitive personal information by default.
- Allowing crawlers or external providers to become CK-NEXUS authority.

## Definition of done for a knowledge answer

An answer is production-grade only when it can expose:

- query and decomposition,
- source list,
- canonical URLs,
- original languages,
- timestamps and freshness,
- content hashes,
- entities and relation paths,
- claim confidence and reliability state,
- contradictory evidence,
- policy decisions,
- audit trail,
- verification state.

This keeps the system aligned with CK-NEXUS evidence-first and fail-closed
principles.
