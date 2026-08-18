# CK-NEXUS Unified Architecture

Status: architecture baseline / non-production

## Purpose
Unify the governed AGNES runtime, provider fabric, assistant registry, evidence system, execution workers, Digital Twin concepts, and Business OS capabilities without treating prototypes as production.

## Canonical authority chain
Human Principal -> Agent Identity -> Capability Lease -> Policy/Reversibility -> Approval Registry -> Credential Reference Broker -> Deny-by-default Sandbox -> Execution Envelope/Journal -> Executor -> Independent Effect Verification -> Evidence Record/Evidence Graph.

## Runtime invariants
- MODEL != AUTHORITY
- AGENT != AUTHORITY
- DISCOVERED != APPROVED
- CONNECTED != WRITE_AUTHORIZED
- AUTHORIZED != EXECUTED
- EXECUTED != VERIFIED
- VERIFIED != PRODUCTION
- LOCAL != STAGING != PRODUCTION
- REDIS EVENT != DURABLE TRUTH
- CREDENTIAL REFERENCE != SECRET VALUE
- SIMULATION != REAL EFFECT

## Layers
1. Sovereign Control Plane: identity, policy, lease, approval, budget, reversibility.
2. Cognitive Fabric: AGNES, planner, verifier, capability resolver, assistants, memory.
3. Execution Fabric: sandbox, execution envelope, Termux/VPS/container workers.
4. Provider Fabric: provider lifecycle, routing, credential references, cost registry, key-pool adapters.
5. Evidence Fabric: durable journal, verification, evidence bundles, signatures, replay/outbox.
6. Digital Twin: state representation and simulation; simulation must never be treated as real execution.
7. Business OS: CRM, leads, sales, marketing, billing, automation, analytics.

## Promotion rule
Existing code is not production merely because it exists. Promotion requires inventory, tests, security evidence, verification, review, and the applicable production gate.

## Current production closure
Q10 Deep Security, Q11 Live Provider, and Q12 delegated cgroup v2 remain hard blockers until fresh evidence proves them for the final release subject.

## Safe integration order
Contracts -> Lease/Budget -> Sandbox Executor -> Credential Adapters -> Evidence Bundle -> Durable Outbox -> Provider Lifecycle -> Real Control-Plane UI.

AGNES, Digital Twin, Marketplace, and sovereign layers must be integrated through these contracts rather than bypassing them.
