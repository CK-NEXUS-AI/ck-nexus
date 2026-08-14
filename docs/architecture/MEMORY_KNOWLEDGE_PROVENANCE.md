# Memory, Knowledge, and Provenance

Status: architecture contract.

## Principle

CK-NEXUS does not treat every observed text, model output, external record, or remembered conversation as truth. Memory is retained context; knowledge is a claim/object with provenance and validation state.

## Memory record

A durable memory record includes tenant, subject/entity references, content or content reference, memory class, source provenance, data classification, retention policy, confidence/validation state, embedding/index metadata, timestamps, access metadata, and redaction/deletion state.

## Knowledge claim

A knowledge claim contains a normalized claim, source(s), extraction method, observed/published timestamps when known, confidence, verification state, contradiction links, applicable scope, freshness policy, and evidence references.

## Provenance

Minimum provenance fields:

- source kind: owner input, connected service, public documentation, provider output, internal execution evidence, imported file, derived summary;
- stable source reference when available;
- observed/retrieved timestamp;
- source/content hash or fingerprint;
- transformation/extraction chain;
- producer/tool/adapter identity and version;
- tenant and data classification;
- licensing/usage note when relevant.

## Truth hierarchy

Operational facts favor fresh authoritative runtime APIs/evidence over stale caches or summaries. External AI output is a candidate claim, not an authority merely because a model produced it.

## Contradictions

Contradictory claims coexist with explicit conflict state until resolved by policy/verification. The system must not silently overwrite a prior claim when sources disagree.

## Retrieval

Retrieval filters tenant and policy before semantic ranking. Ranking may consider relevance, authority, freshness, validation, provenance quality, and task fit. High-confidence stale knowledge can still be inappropriate for current-state questions.

## Learning

Learning updates indexes, scores, routing statistics, evaluation artifacts, user-approved preferences, and validated knowledge. It does not modify model weights implicitly or claim to extract proprietary hidden model internals.

## Evidence

Important promoted knowledge/capabilities preserve the chain from original source to normalized object to validation evidence and promotion decision.
