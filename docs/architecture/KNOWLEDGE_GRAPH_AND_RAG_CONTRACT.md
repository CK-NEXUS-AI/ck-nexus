# Knowledge Graph and RAG Contract

Status: architecture contract.

## Separation

Raw source objects, parsed chunks, embeddings, graph entities/relations, knowledge claims, summaries and retrieval caches are separate layers with provenance links.

## Ingestion

Source -> content fingerprint -> parser/extractor -> chunks -> entities/relations/claims -> validation/classification -> embedding/index -> retrieval eligibility.

## Stable identity

Documents/objects receive stable source IDs and version/content hashes. Reingestion of unchanged content is idempotent. Changed content creates a new version and invalidates affected derived artifacts.

## Retrieval contract

A retrieval request specifies tenant, query/task, allowed source classes, data classification, freshness needs, maximum evidence age, top-k/budget, and citation requirement.

Retrieval output returns ranked evidence items with source reference, chunk/object ID, content hash, score breakdown when practical, observed/published time, authority/freshness, and access/policy state.

## Graph

Graph edges are typed and provenance-backed. Derived/inferred edges are marked separately from direct source assertions. Confidence and temporal validity may be attached to edges/claims.

## RAG answer generation

The generator receives bounded retrieved evidence, not unrestricted storage. The verifier checks whether material claims are supported when grounding is required. Unsupported claims are flagged or omitted according to policy.

## Cache safety

Retrieval/answer caches bind tenant, authorization context, source versions, policy hash, and relevant freshness window. Cross-tenant cache leakage is forbidden.
