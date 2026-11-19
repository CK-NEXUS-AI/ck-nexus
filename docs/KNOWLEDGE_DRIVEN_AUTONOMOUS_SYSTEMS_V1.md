# CK-NEXUS Knowledge-Driven Autonomous Systems Capability Framework V1

Status: Post-P0 development candidate.
Authority: CK-NEXUS.
Production effect: none.
Q10/Q11/Q12 effect: none.

## Purpose

This framework turns research from a one-shot search step into a governed,
measurable loop that can recognize missing knowledge, expand discovery,
separate copied evidence from independent evidence, preserve contradictions,
compile reusable research artifacts, and route unresolved uncertainty to
additional research or human review.

It extends the Universal Command Intake & Execution Protocol and Global
Knowledge Filtering V1. It does not create a second execution authority.

## Eight capability areas

### 1. Knowledge gap detection

The system represents gaps explicitly rather than assuming that available
knowledge is sufficient.

Current gap classes:

- MISSING: no admitted evidence exists.
- WEAK: evidence count or independent lineage count is below a declared minimum.
- CONTRADICTION: mutually exclusive claims remain unresolved.
- STALE: evidence is too old or undated for the declared freshness requirement.
- COVERAGE: required language, region, source class, or technical aspect is missing.

A gap records whether further research can resolve it and which search-expansion
strategies should run.

### 2. Evidence independence

Source count and independent evidence count are different metrics.

Every admitted source may carry a lineage identifier. Multiple pages that share
one lineage are one evidence family even when the URLs or domains differ.

The framework records:

- source count,
- lineage count,
- independent lineage count,
- validated lineage count,
- duplicate/syndicated lineages,
- source-to-lineage mapping.

Independent validation is tracked separately from lineage membership.

### 3. Contradiction detection

Deterministic contradiction detection is intentionally conservative.

The current implementation detects conflicting values only for predicates that
the caller explicitly marks as exclusive. Time-disjoint historical values are
not automatically treated as contradictions.

Semantic, pragmatic, or logical contradictions that require interpretation are
not guessed by deterministic code. They require a later independent analysis
adapter and remain reviewable evidence.

### 4. Search expansion

Search expansion reuses the strategies introduced by Global Knowledge Filtering
V1:

- independent sources,
- source diversity,
- language coverage,
- freshness,
- alternative terminology,
- primary sources.

A research artifact containing unresolved gaps emits structured
SearchExpansion objects. These are planning inputs, not permission to bypass
crawl policy.

### 5. Coverage analysis

Coverage is measured only against declared research requirements. CK-NEXUS must
not claim coverage of the whole internet or an unknown universe of sources.

Measured dimensions include:

- admitted source minimum,
- independent lineage minimum,
- primary-source minimum,
- required languages,
- required regions,
- required source classes,
- required technical aspects,
- freshness.

An unspecified dimension is represented as unscoped rather than silently
reported as complete.

### 6. Autonomous research architecture

The operational research loop is:

User/Protocol intent
-> recall existing work
-> discovery
-> filtering
-> research compilation
-> coverage/lineage/diversity analysis
-> contradiction/gap detection
-> search expansion when needed
-> analysis when declared requirements are satisfied
-> verification/review
-> append learning

The research compiler produces a durable-shaped artifact containing source IDs,
claim IDs, lineage analysis, coverage, diversity, contradictions, gaps, and
expansion directives. The artifact is not itself release evidence.

### 7. Source diversity

Diversity is reported across:

- languages,
- regions,
- source classes,
- independent evidence lineages,
- primary sources.

The score is scoped to declared requirements. Geographic or viewpoint diversity
does not automatically imply correctness, and source reputation alone does not
verify a claim.

### 8. Citation graph and evidence lineage

The evidence graph supports:

- SOURCE and CLAIM nodes,
- CITES edges,
- DERIVED_FROM edges,
- SUPPORTS edges,
- CONTRADICTS edges.

Lineage tracing walks from a current source or claim toward its upstream roots
and records depth and explicit independent-validation edges.

The implementation does not assume every citation graph is acyclic. Citation
cycles are detected and reported rather than hidden or forcefully rewritten.

## Gen 6.1 to Gen 6.4 implementation map

### Gen 6.1: Research sufficiency core

Implemented:

- declared research requirements,
- coverage analysis,
- source diversity analysis,
- evidence-lineage grouping,
- knowledge-gap detection,
- research compilation artifact,
- automatic research-cycle decision,
- Master Controller-compatible routing plan.

### Gen 6.2: SearXNG discovery

Implemented as a discovery-only adapter.

Current official SearXNG API usage:

- GET /search,
- q parameter,
- format=json,
- optional language/categories/time_range,
- JSON must be enabled by the configured SearXNG instance.

Search results are discovery candidates, not verified evidence.

### Gen 6.3: Crawl4AI governed crawl

Implemented as an optional lazy-loaded provider adapter.

The provider path uses the current Crawl4AI configuration model:

- AsyncWebCrawler,
- BrowserConfig,
- CrawlerRunConfig,
- arun(url=..., config=...).

CK-NEXUS crawl policy executes before the provider. The adapter does not disable
browser sandboxing, bypass robots/terms/privacy controls, or support
CAPTCHA/paywall/credential bypass.

The default project dependency set remains unchanged. If Crawl4AI is absent the
adapter reports PROVIDER_UNAVAILABLE instead of silently falling back.

AdaptiveCrawler coverage/consistency/saturation can be integrated later as
provider observations, but CK-NEXUS remains the authority for final research
sufficiency.

### Gen 6.4: Contradiction and lineage

Implemented:

- deterministic exclusive-predicate contradiction records,
- time-disjoint conflict suppression,
- evidence graph nodes and edges,
- upstream lineage tracing,
- citation cycle detection,
- unresolved contradiction routing to human review after research exhaustion.

## Master Controller integration boundary

The research bridge emits one of three states:

- CONTINUE_RESEARCH:
  lanes web_research + agnes + evidence.
- READY_FOR_ANALYSIS:
  lanes agnes + evidence.
- HUMAN_REVIEW_REQUIRED:
  lanes agnes + evidence with a human gate.

The bridge creates a controller-compatible intent. It does not execute the
Master Controller or external tools itself.

## Provider evidence boundary

SearXNG and Crawl4AI are workers/providers only.

They cannot:

- mark claims VERIFIED,
- change Q10/Q11/Q12,
- authorize Production,
- approve their own output,
- override crawl policy,
- become canonical truth stores.

## Research completion rule

Research may enter analysis when declared high-severity gaps and deterministic
contradictions are cleared.

This state means sufficient-for-analysis under the declared scope. It does not
mean VERIFIED.

If contradictions remain after the allowed research budget is exhausted, the
system routes to HUMAN_REVIEW_REQUIRED.

## External research claims

Named academic frameworks, benchmark percentages, and third-party performance
claims are not hard-coded into this implementation unless their exact source
and evidence are separately verified. The architecture adopts reusable
principles rather than unverified marketing or benchmark numbers.

## Next integration targets

1. Persist ResearchCompilationArtifact through Knowledge Persistence V2.
2. Feed SearchExpansion objects into the active Master Controller Web Research lane.
3. Add a configured self-hosted SearXNG runtime.
4. Add an isolated Crawl4AI runtime with network resource controls.
5. Add semantic contradiction review as an independent worker.
6. Add bitemporal claim state and evidence graph persistence.
7. Add benchmark suites for research sufficiency, source independence, and gap
   closure quality.
8. Keep complex results at MEASURED_NOT_VERIFIED until independent verification
   requirements are satisfied.
