# CK-NEXUS Cognitive Knowledge System Boundaries - 2026.09

Status: DEVELOPMENT CANDIDATE / NOT VERIFIED / NOT PRODUCTION

## Purpose

CK-NEXUS has accumulated several knowledge, memory, claim and learning experiments on historical
branches. They must not become parallel authorities. This document assigns one responsibility to
each reusable subsystem and defines how they interoperate without duplicating truth.

## 1. Knowledge Fabric

Role: source and knowledge-claim runtime.

Owns:

- source provenance and content identity
- tenant boundary for knowledge retrieval
- FACT / OPINION / INFERENCE / PREDICTION / ASSUMPTION separation
- temporal freshness
- source revocation eligibility
- contradictions and supersession relationships
- retrieval ranking signals
- proposal-only memory writes
- mapping into the existing IdeaGraph

Does not own:

- security/release verification authority
- capability adoption decisions
- provider credentials
- production promotion
- independent verification

## 2. IdeaGraph / Idea Engine

Role: graph projection and relationship workspace.

Owns:

- idea/evidence/assumption/risk/opportunity/decision/action nodes
- typed relationships such as supports, contradicts, refines and depends_on
- graph traversal and audit history already implemented by the Idea Engine

Knowledge Fabric extends this graph. It does not create a second graph authority.

## 3. Claim Registry

Historical source: `post-p0/claim-registry-v1`.

Role: governance claim state and publication discipline.

Reusable properties:

- TARGET -> MEASURED_NOT_VERIFIED -> VERIFIED/REJECTED state machine
- benchmark and evidence digest requirements
- append-only state history
- self-certification prohibition
- stale publication state when the exact subject commit changes

The Claim Registry is not a factual knowledge store. Knowledge claims may reference governance claim
identifiers/evidence, but FACT confidence must never promote a governance claim to VERIFIED.

## 4. AGNES Knowledge Repository

Historical source: `post-p0/agnes-knowledge-repository-v1`.

Role: pre-development capability/reuse catalog.

Reusable properties:

- PENDING_REVIEW / STUDYING / UNDERSTOOD / ADOPTABLE / ADOPTED / REJECTED lifecycle
- ADOPT / WRAP / STUDY / AVOID consumption modes
- reuse-first predevelopment search
- capability matching
- bounded two-strike stop-and-research behavior

This repository answers: "Does CK-NEXUS already know of a reusable capability or implementation?"
It does not answer: "Is an external factual claim true?"

## 5. AGNES Learning Consolidator

Historical source: `post-p0/agnes-learning-consolidator-v1`.

Role: evidence-bound learning proposal engine.

Reusable properties:

- PROPOSE / BLOCK / QUARANTINE
- semantic fingerprints to prevent duplicate learning deltas
- measured-ratio and score thresholds
- contradiction/rejection quarantine
- explicit supersession while preserving history
- append-only hash-chained learning ledger
- verification ceiling of MEASURED_NOT_VERIFIED
- independent verification and experiment required
- adoption, auto-activation, external action and production mutation disabled

Current canonical main does not contain the Triad Pulse dependency required by this historical module.
Therefore the module is a REUSE_CANDIDATE and must not be copied into current runtime in isolation.
Dependency reconciliation is required first.

## 6. Connected Source Intelligence

Historical source: `post-p0/agnes-connected-source-intelligence-v1`.

Role: source-ingestion policy and data-minimization guidance.

Reusable policies:

- task-specific metadata-first discovery
- external content remains untrusted
- do not persist raw mailbox/Drive content by default
- prefer structured facts, hashes, timestamps and provenance
- secret/credential exclusion
- no source text may grant approval, policy or production authority
- mutations remain separately governed

The historical branch primarily records policy/evidence boundaries. It does not prove a complete
canonical source-ingestion runtime. Status: REUSE_POLICY / RUNTIME_GAP.

## 7. Memory

Role: governed retention of approved memory records.

The Knowledge Fabric may only emit a MemoryWriteProposal. A separate memory authority must evaluate:

- tenant/subject
- consent
- data classification
- retention class
- expiry
- source access/revocation
- supersession
- privacy/security policy

Learning is not permission to remember everything.

## 8. Retrieval order

The required order is:

1. authenticate subject/tenant context;
2. apply tenant and authorization/policy filters;
3. remove revoked or stale ineligible material;
4. apply source/claim constraints;
5. perform lexical/semantic retrieval;
6. rank eligible results;
7. preserve contradictions;
8. synthesize with citations/provenance;
9. label factual, inferential and predictive output separately.

Semantic similarity must never run before tenant/policy filtering when doing so could expose
cross-boundary data.

## 9. Single-authority rule

There is one canonical truth per concern:

- factual/source truth: Knowledge Fabric contracts
- graph projection: IdeaGraph
- governance claim state: Claim Registry
- capability reuse decision: AGNES Knowledge Repository
- learning proposal: Learning Consolidator
- memory retention: governed memory layer
- release/security authority: existing CK-NEXUS gates and independent verification

No subsystem may silently assume another subsystem's authority.

## 10. V2 implementation order

1. Complete tenant/hash/revocation/temporal compatibility in Knowledge Fabric.
2. Prove regression and security tests.
3. Add PostgreSQL persistence behind a repository interface, reusing existing PostgreSQL runtime.
4. Add policy-filtered lexical retrieval baseline.
5. Benchmark semantic/vector retrieval against that baseline.
6. Adopt a vector adapter only if it adds measurable retrieval quality/performance or a missing
   capability.
7. Reconcile Triad Pulse dependencies before restoring Learning Consolidator runtime.
8. Add connected-source adapters only through existing connector/credential/trust boundaries.

No item in this order authorizes merge, production deployment or self-verification.
