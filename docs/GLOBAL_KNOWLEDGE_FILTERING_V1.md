# Global Knowledge Automatic Filtering V1

Status: Post-P0 development only.
Authority: CK-NEXUS.
Production effect: none.

## Goal

Filter discovered information before knowledge admission and automatically
request broader research when evidence is too narrow, duplicated, stale, or
low quality.

The filter is deterministic and dependency-light. Search and crawler
providers remain replaceable workers.

## Decision model

Each candidate receives one action:

- ACCEPT: admissible as observed development knowledge.
- REJECT: policy or exact-provenance failure.
- QUARANTINE: preserve for audit, but do not admit as independent knowledge.

Filtering never promotes a candidate or claim to VERIFIED.

## Inputs

A candidate includes:

- canonical SourceRef provenance,
- crawl-policy decision,
- extracted text,
- extraction confidence,
- optional evidence-lineage identifier,
- optional age in seconds.

## Filtering order

1. Crawl policy.
2. Provenance presence.
3. Exact content-hash duplicate.
4. Minimum extracted content.
5. Extraction quality.
6. Request-specific freshness.
7. Syndication/evidence-lineage duplication.
8. Admission as OBSERVED.

The order is intentional. Policy and provenance failures take precedence over
quality scoring.

## Search expansion

After filtering a batch, CK-NEXUS evaluates information sufficiency.

Expansion directives are emitted when:

- accepted source count is below the configured minimum,
- independent evidence lineages are below the configured minimum,
- required languages are missing,
- required source classes are missing,
- duplicate or syndicated evidence is detected,
- stale candidates are detected.

Expansion strategies include:

- independent sources,
- source diversity,
- language coverage,
- freshness,
- alternative terminology,
- primary sources.

These directives are planning inputs. They do not bypass authorization,
robots, terms, jurisdiction, privacy, rate limits, or evidence gates.

## Provider integration

SearXNG can be used as a discovery provider for query expansion. JSON output
must be explicitly enabled on the configured instance.

Crawl4AI can be used later as a crawl provider. Its adaptive crawler exposes
coverage, consistency, and saturation signals that can be mapped into CK-NEXUS
research sufficiency without making Crawl4AI an authority.

## Evidence independence

Two pages are not independent evidence merely because they have different
URLs or domains. A lineage identifier may represent a shared wire story,
syndicated article, copied press release, mirrored document, or other common
origin.

Exact duplicates are rejected from knowledge admission. Repeated lineages are
quarantined so they remain auditable without inflating corroboration.

## Safety boundaries

The filter must not:

- bypass crawl policy,
- infer permission from availability,
- treat generated text as external evidence,
- convert OBSERVED into VERIFIED,
- delete original evidence,
- count syndicated copies as independent confirmation,
- modify Q10/Q11/Q12 state,
- declare Production readiness.

## Next integration

1. Connect Search-Before-Solve to the filter result.
2. Persist filter decisions and attempts through Knowledge Persistence V2.
3. Route expansion directives through Master Controller.
4. Add SearXNG discovery adapter.
5. Add Crawl4AI adapter behind crawl policy.
6. Add contradiction and claim-level corroboration.
7. Add independent review and benchmark evidence.
