# CK-NEXUS Unified Architecture Index

Status: architecture package index. Runtime/release authority remains with release gates and evidence.

## Purpose

This file is the navigation root for the post-Q09 CK-NEXUS target architecture. It keeps the design as one coherent operating system rather than a collection of independent demos.

## Planes

### Cognitive Plane

Intent/context, Cognitive Governor, model/worker routing, reasoning/planning algorithms, consensus, uncertainty, memory/knowledge and evaluation.

Primary contracts:

- `COGNITIVE_GOVERNOR_AND_CONSENSUS.md`
- `COGNITIVE_MODE_SELECTION.md`
- `MODEL_EVALUATION_SCORECARD.md`
- `UNCERTAINTY_AND_CONFLICT_RESOLUTION.md`
- `CONTEXT_AND_PROMPT_TRUST_BOUNDARY.md`
- `MEMORY_KNOWLEDGE_PROVENANCE.md`
- `KNOWLEDGE_GRAPH_AND_RAG_CONTRACT.md`

### Control Plane

Identity/tenant, policy/risk, approvals, capability registry, connector state, command API, incident/recovery, budgets, evidence gates and operator UX.

Primary contracts:

- `CONTROL_PLANE_API_CONTRACT.md`
- `APPROVAL_AUTHORITY_MODEL.md`
- `CAPABILITY_RESOLUTION_AND_SCORING.md`
- `CONNECTOR_LIFECYCLE_AND_HEALTH.md`
- `INCIDENT_RECOVERY_CONTROL_MODEL.md`
- `OBSERVABILITY_SLO_CONTRACT.md`
- `EVIDENCE_FRESHNESS_AND_PROVENANCE.md`

### Execution Plane

AGNES task DAG, durable action journal, provider/connectors/tools/skills, retry/fallback, reconciliation, verification, compensation/recovery and execution receipts.

Primary contracts:

- `AGNES_TASK_STATE_MODEL.md`
- `DURABILITY_IDEMPOTENCY_RECONCILIATION.md`
- `ERROR_TAXONOMY_AND_FALLBACK.md`
- `PROVIDER_SEMANTIC_CONTRACT.md`
- `RECOVERY_RTO_RPO_AND_DRILL.md`
- `ROLLBACK_AND_COMPENSATION_POLICY.md`

## Shared Fabrics

Connection Fabric discovers/binds systems. Capability Fabric declares/resolves semantic ability. Event Fabric transports causal events. Automation Fabric composes workflows. Trust Fabric governs identity/credentials/policy/risk/approval. Evidence Fabric records verification/provenance/release evidence.

## External runtimes

Base44/Solas and future external runtimes are adapters/execution resources, not CK authority. Read `BASE44_CKNEXUS_FEDERATION.md`, `BASE44_CKNEXUS_RECONCILIATION.md`, and `EXTERNAL_CAPABILITY_NORMALIZATION_PIPELINE.md`.

## Marketplace and self-expansion

All discovered/generated artifacts enter quarantine/candidate lifecycle and cannot self-promote. Read `MARKETPLACE_TRUST_SUPPLY_CHAIN.md`, `SKILL_CAPABILITY_INGESTION.md`, `BRAIN_UPGRADE_ENGINE_REDESIGN.md`, `SIMULATION_SHADOW_CANARY.md`, and Gen3/self-expansion contracts.

## Operator surface

The Unified Command Center is the human control surface. It consumes Control Plane contracts and never directly owns provider credentials or bypasses AGNES for impactful side effects.

## Release authority

Architecture completeness is not Production GO. Canonical main remains governed by Q01-Q16; Q10 is the earliest incomplete gate in the current program. Draft architecture branches must not be used as release evidence merely because CI is green.
