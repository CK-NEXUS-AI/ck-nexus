# CK-NEXUS Autonomous Platform Fabric — Gen3 Extensions

Status: SPEC_ONLY

This document extends the six Gen2 fabrics without changing their authority boundaries. It adds optional cross-cutting fabrics for simulation, time, learning, resource economy, sovereignty, human collaboration, marketplace trust, and semantic context.

## Invariants

1. No AI provider, agent, tool, skill, connector, or workflow may directly bypass Trust Fabric or AGNES execution controls.
2. All impactful side effects require policy evaluation and evidence receipts.
3. Self-expansion may create candidates, but cannot self-promote to trusted/production state.
4. Production mutation remains disabled unless explicitly enabled by owner policy and release gates.
5. Gen3 components are replaceable plugins and communicate through contracts/events, not pairwise imports.

## Gen3 fabrics

### Simulation Fabric

Purpose: evaluate candidate actions before execution.

Responsibilities:
- digital-twin state snapshots
- what-if execution plans
- blast-radius estimation
- policy simulation
- failure injection models
- rollback feasibility scoring
- counterfactual comparison

Outputs are advisory evidence only; simulation never authorizes execution.

### Temporal Fabric

Purpose: make time a first-class control dimension.

Responsibilities:
- deadlines and temporal constraints
- lease/TTL semantics
- event-time versus processing-time
- schedule windows and quiet periods
- freshness requirements
- stale-evidence detection
- time-bounded approvals
- delayed/compensating actions

### Learning and Evaluation Fabric

Purpose: improve routing and planning using verified outcomes rather than ungrounded self-modification.

Responsibilities:
- benchmark registry
- capability evaluation
- historical quality scores
- regression baselines
- routing feedback
- drift detection
- novelty/deduplication
- provenance-backed lessons

Only evidence-backed observations may update trusted capability metadata.

### Resource Economy Fabric

Purpose: optimize constrained resources safely.

Responsibilities:
- budget policy
- quota telemetry
- latency/cost tradeoffs
- energy/compute hints
- rate-limit awareness
- free/local preference modes
- reserved-capacity decisions

It must never create accounts, rotate identities, or evade provider quotas/terms.

### Sovereignty Fabric

Purpose: enforce tenant, geography, privacy, and data-residency constraints.

Responsibilities:
- data residency
- model/provider jurisdiction policy
- tenant isolation
- export restrictions
- local-only modes
- sensitive-data routing
- retention/deletion obligations

### Human Collaboration Fabric

Purpose: make human authority explicit in autonomous workflows.

Responsibilities:
- approval queues
- role-aware review
- explainability packets
- escalation policies
- manual intervention
- pause/resume/abort
- ownership transfer

### Marketplace and Supply-Chain Fabric

Purpose: evaluate external agents, skills, models, prompts, connectors, and workflows before registration.

Responsibilities:
- package identity
- signatures and provenance
- dependency metadata
- publisher trust
- license metadata
- vulnerability status
- compatibility contracts
- promotion channels: discovered -> candidate -> verified -> canary -> trusted

### Semantic Context Fabric

Purpose: preserve meaning across agents, providers, tools, workflows, and events.

Responsibilities:
- canonical intent representation
- shared entity identities
- context envelopes
- ontology/schema mapping
- semantic versioning
- conflict detection
- context compression with provenance

## Core Gen3 primitives

### Capability Topology Graph

A durable graph connecting:
- capabilities
- manifests
- providers
- agents
- skills
- tools
- connectors
- policies
- data classes
- environments
- dependencies
- observed reliability

The planner queries this graph instead of hardcoding integrations.

### Intent Compiler

Transforms natural-language goals into an immutable IntentSpec before planning.

IntentSpec includes:
- goal
- constraints
- forbidden actions
- required evidence
- budget
- risk ceiling
- environment
- approval policy
- freshness constraints

### Portable Agent Capsule

A provider-neutral package containing:
- agent manifest
- declared capabilities
- allowed tools
- model requirements
- memory policy
- input/output contracts
- evaluation profile
- security policy references

### Verification Mesh

Multiple independent verifiers can validate execution results by domain:
- contract verifier
- policy verifier
- security verifier
- semantic verifier
- data-integrity verifier
- business-rule verifier

Disagreement becomes an explicit conflict event, not silent success.

### Shadow Autonomy

New autonomous policies first run in shadow mode:
- observe real tasks
- produce plans
- do not execute side effects
- compare predicted versus actual operator outcomes
- collect evidence
- promote only after review

## Gen3 decision flow

Intent
-> Intent Compiler
-> Semantic Context
-> Alternative Task DAGs
-> Capability Topology Graph
-> Simulation
-> Policy/Risk/Cost/Sovereignty/Time evaluation
-> Human approval when required
-> Credential lease
-> Proof-Carrying AGNES execution
-> Verification Mesh
-> Evidence + Durable Action Journal
-> Event Fabric
-> Reconciliation
-> Learning/Evaluation

## Failure semantics

Every failure must be classified into one of:
- transient
- permanent
- authorization
- policy_denied
- quota_exhausted
- contract_violation
- data_conflict
- partial_side_effect
- unknown_outcome
- infrastructure
- security

Unknown outcome is never treated as safe retry. Reconciliation/evidence lookup occurs first.

## Adoption order

1. Contracts and schemas
2. Capability topology read model
3. IntentSpec and semantic context envelopes
4. Simulation and shadow-mode interfaces
5. Proof-carrying execution receipts
6. Durable action journal and reconciliation
7. Learning/evaluation feedback
8. Marketplace trust and promotion

Runtime implementation is blocked by the current Q10 security gate and must be introduced incrementally after re-baselining.