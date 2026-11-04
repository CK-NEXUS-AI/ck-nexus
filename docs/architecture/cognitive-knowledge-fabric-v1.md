# CK-NEXUS Cognitive Knowledge Fabric V1

Status: DEVELOPMENT CANDIDATE / NOT VERIFIED / NOT PRODUCTION

## Purpose

Cognitive Knowledge Fabric V1 extends the existing Idea Engine rather than replacing it. The goal is
to make knowledge ingestion, comparison and synthesis explicit about provenance, freshness, claim
class and authority boundaries before adding vector databases, graph databases or autonomous
learning loops.

## Reused canonical components

- IdeaGraph and Idea Engine
- existing evidence/assumption node model
- Unified Memory and session/run history
- Connector Fabric and integration boundaries
- Provider Router and Credential Broker
- AGNES/development orchestration
- existing security, approval and release gates

## New V1 contracts

### SourceRecord

Required source metadata:

- stable source id
- source class
- locator
- title
- retrieval time
- trust score
- language
- optional author/publisher/publication time
- rights status
- non-secret metadata

A trust score is ranking metadata. It is not independent verification.

### KnowledgeClaim

Every claim carries:

- claim id
- subject
- predicate
- value
- claim class
- source references
- confidence
- observation time
- verification state
- optional qualifiers

Canonical claim classes:

- FACT
- OPINION
- INFERENCE
- PREDICTION
- ASSUMPTION

The UI and synthesis layers must preserve those distinctions.

## Conflict handling

V1 provides deterministic conflict detection for claims sharing the same normalized subject and
predicate but containing different values. It preserves both claims and their source references.
It does not resolve conflicts by deleting one side or by treating model confidence as authority.

Future semantic conflict resolution may add model-assisted comparison, but the deterministic layer
remains the audit baseline.

## Freshness and quality

Source ranking combines declared trust metadata, retrieval freshness and claim confidence. The
freshness score decays over time and is computed independently of model output.

This ranking is only a retrieval/synthesis signal. It must never become a release, security or
verification gate by itself.

## Memory learning boundary

The Knowledge Fabric may propose a memory write. It may not approve its own proposal.

Every proposed write contains:

- content
- source claim ids
- memory scope
- retention period
- consent-required flag
- auto-approved=false

Protected authority scopes cannot be mutated by the Knowledge Fabric:

- policy
- approval
- release gate
- credential state

This preserves the CK-NEXUS rule that learning cannot self-authorize or change production authority.

## Idea Graph integration

Knowledge claims map into the existing IdeaNode model:

- factual claims -> evidence nodes
- non-factual claims -> assumption nodes
- source references are preserved
- confidence remains metadata

No second graph database is introduced in V1.

## Future deltas

V2 candidates, only after benchmark and security review:

1. PostgreSQL persistence for source and claim records.
2. Vector retrieval adapter with a provider-neutral interface.
3. Semantic chunking and citation spans.
4. Temporal knowledge and supersession relationships.
5. Claim-level contradiction detection with typed evidence.
6. Cross-language retrieval and normalized source identities.
7. Source-quality policies by domain.
8. Graph analytics over IdeaGraph plus knowledge claims.
9. Incremental feedback evaluation with explicit consent.
10. OpenTelemetry spans for search, retrieval, synthesis and memory proposals.

Graph/vector products are implementation adapters, not architectural authorities. A new database is
adopted only if it beats the existing baseline or adds a capability that cannot be achieved safely
with current storage.

## Explicit non-goals

V1 does not claim:

- universal knowledge
- autonomous policy modification
- automatic production deployment
- automatic acceptance of web content as fact
- hidden chain-of-thought disclosure
- permanent memory of every interaction
- unrestricted crawling of websites
- bypass of authentication, robots, copyright or access controls
- gRPC or Next.js runtime adoption

## Acceptance criteria

V1 is eligible for further review only when:

- existing Idea Engine tests still pass
- new Knowledge Fabric tests pass
- Ruff/Bandit/secret scanning pass
- conflict behavior is deterministic
- provenance is mandatory
- protected memory scopes fail closed
- no production/frozen-Q10 files are changed
- independent review remains separate from implementation
