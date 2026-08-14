# Skill and Capability Ingestion

Status: architecture contract.

## Goal

Only ingest net-new, usable semantic capability or knowledge. Avoid duplicate skills whose only difference is provider branding.

## Pipeline

`DISCOVER -> EXTRACT -> NORMALIZE -> DEDUPE -> POLICY -> CONTRACT -> EVALUATE -> QUARANTINE|CANDIDATE -> CANARY -> PROMOTE`

## Discovery sources

Allowed sources include public/official docs, owner-provided files/outputs, connected service metadata, installed plugin manifests, provider capability metadata, internal evaluations, and approved marketplace artifacts.

Discovery never authorizes scraping inaccessible/private model internals, copying proprietary weights, or obtaining hidden prompts/skills.

## Semantic normalization

A provider feature maps to a semantic capability ID such as `research.web.search_grounded`, `code.generate`, or `support.ticket.read`. Provider-specific implementation details live under the candidate implementation, not the semantic ID.

## Deduplication

Dedup uses exact IDs plus semantic similarity, input/output contract equivalence, side-effect semantics, and intended task class. A newly observed implementation may improve an existing capability without increasing unique-capability count.

## Minimum valid skill candidate

A skill candidate requires non-null ID/name, semantic capability IDs, input/output contract, provenance, lifecycle state, risk/side-effect classification, implementation/runtime reference, validation state, and evidence requirements.

Missing identity/provenance/contract -> `QUARANTINED_MALFORMED`.

## Evaluation

Evaluation may measure contract correctness, task quality, grounding, latency, cost, reliability, security/policy behavior, and historical success. Scores are evidence, not permission.

## Promotion

Promotion to stable registry requires policy-defined evidence. Self-generated code/content cannot self-promote. High-impact capability requires stronger review and canary controls.

## Counts

Published counts distinguish:

- observed external records;
- valid candidates;
- verified implementations;
- unique semantic capabilities;
- stable/promoted capabilities.

A counter is never derived from the number of database rows alone.
