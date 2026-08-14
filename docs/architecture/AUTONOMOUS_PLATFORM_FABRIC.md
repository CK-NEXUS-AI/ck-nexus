# CK-NEXUS Autonomous Platform Fabric

Status: SPEC_ONLY
Parent architecture branch: `arch/monorepo-layered-v01`
Purpose: evolve CK-NEXUS from a layered monorepo into a policy-controlled, contract-driven autonomous platform fabric without coupling AGNES, providers, tools, connectors, automation, or applications directly to one another.

## Core laws

1. Everything executable is a Capability.
2. Everything discoverable exposes a Manifest.
3. Everything composable exposes a Contract.
4. Everything asynchronous emits Events through a shared envelope.
5. Everything identity-sensitive is bound to Trust Fabric.
6. Everything state-changing is approval-aware and idempotent.
7. Everything important emits Evidence.
8. Everything replaceable is plugin-based.
9. Everything stateful uses durable storage appropriate to its semantics.
10. Everything risky can fail closed.
11. No provider, connector, tool, skill, or agent may bypass governance to execute external side effects directly.
12. No self-expansion candidate may self-promote to production.

## Three planes

### Cognitive Plane
Understands intent, context, alternatives, model/tool selection, prediction, evaluation, memory, knowledge, consensus, and planning.

Primary components:
- `intelligence/intent_graph`
- `intelligence/context_engine`
- `intelligence/reasoning`
- `intelligence/alternative_planner`
- `intelligence/capability_router`
- `intelligence/model_router`
- `intelligence/tool_router`
- `intelligence/conflict_resolver`
- `intelligence/prediction`
- `intelligence/evaluator`
- `intelligence/knowledge_graph`
- `intelligence/graph_rag`

### Control Plane
Owns authority, trust, policy, risk, quotas, approvals, tenancy, data classification, change control, release promotion, and evidence acceptance.

Primary components:
- `platform/trust_fabric`
- `platform/capability_fabric`
- `governance`
- `security`
- `services/cognitive_governor`
- `services/verifier`
- `services/audit`
- `platform/evidence_fabric`

### Execution Plane
Performs approved operations through AGNES and adapters. It does not decide policy.

Primary components:
- `agnes`
- `platform/automation_fabric`
- `platform/connection_fabric`
- `integrations`
- `providers`
- `automation`

## Six shared fabrics

### 1. Connection Fabric
Responsibility: discover, authenticate, probe, connect, fail over, and model topology of external systems.

Subcomponents:
- discovery
- registry
- connector factory
- capability probe
- auth negotiation
- health monitor
- failover
- topology

A connection becomes usable only after the lifecycle:
`DISCOVERED -> AUTH_REQUIRED -> AUTHORIZED -> PROBED -> REGISTERED -> ACTIVE`.

Any failed authorization, failed probe, stale credential lease, contract mismatch, or denied policy causes fail-closed state.

### 2. Capability Fabric
Responsibility: convert providers, agents, tools, skills, connectors, workflows, and selected internal services into a common searchable capability graph.

Every capability advertises:
- stable capability ID
- semantic description
- version
- input/output schema references
- risk class
- side-effect class
- cost/quota metadata
- latency/availability metadata
- data-boundary requirements
- required credentials
- supported events
- evidence requirements

Capability resolution is multi-dimensional rather than a hardcoded router table.

Candidate score may combine:
`task_fit + health + policy_fit + trust + evidence_quality + latency + cost + quota + historical_accuracy`.

### 3. Event Fabric
Responsibility: decouple modules by durable typed events.

Required properties:
- schema validation
- correlation ID and causation ID
- producer identity
- tenant/session/execution scope
- immutable event ID
- versioned event type
- replay support
- dead-letter support
- ordering key where required
- idempotency key for side-effect workflows
- evidence reference for consequential events

Events never grant authority. They only communicate facts or requests. Consumers must independently re-evaluate policy and capability grants before mutations.

### 4. Automation Fabric
Responsibility: compile intent/rules/events/schedules into resumable workflow execution.

Pipeline:
`Trigger -> Normalize -> Resolve Capabilities -> Build DAG -> Policy/Risk -> Credential Lease -> Execute -> Verify -> Compensate/Retry -> Evidence -> Commit State -> Emit Event`.

Execution is checkpointed so a crash or provider failure can resume without duplicating side effects.

### 5. Trust Fabric
Responsibility: unify identity, credential leases, permissions, policy, risk, and approvals.

Principles:
- least privilege
- short-lived leases where supported
- no credential exposure to model prompts
- no automatic account creation
- no quota/rate-limit evasion
- credential rotation only among owner-authorized credentials
- semantic commit guard before high-impact mutation
- explicit approval for high-impact/destructive/production operations
- kill switch evaluated before dispatch and before commit

### 6. Evidence Fabric
Responsibility: turn every important action into independently verifiable evidence.

Evidence classes:
- intent evidence
- authorization evidence
- plan evidence
- execution evidence
- external effect evidence
- verification evidence
- policy decision evidence
- security evidence
- recovery evidence
- release evidence
- provenance attestations

A successful API response alone is not sufficient proof of a business side effect. Evidence validators must confirm the postcondition when practical.

## Universal execution flow

```text
User / Event / Schedule / API
        |
        v
Intent + Context
        |
        v
Task DAG / Alternative Plans
        |
        v
Capability Fabric
        |
        v
Policy + Risk + Cost + Quota
        |
        v
Trust Fabric -> Capability Grant + Credential Lease
        |
        v
AGNES Execution Kernel
        |
        v
Provider / Tool / Skill / Connector
        |
        v
Postcondition Verification
        |
        +--> failure classifier -> retry/fallback/compensation/replan
        |
        v
Evidence Fabric
        |
        v
Durable Commit
        |
        v
Event Fabric
        |
        v
Next workflow / notification / learning signal
```

## Plugin categories

CK-NEXUS treats the following as first-class plugin families:
- ProviderPlugin
- ConnectorPlugin
- ToolPlugin
- SkillPlugin
- AgentPlugin
- WorkflowPlugin
- VerifierPlugin
- EvidenceCollectorPlugin
- PolicyPlugin
- StoragePlugin

Each family uses the same discovery lifecycle and shared manifest rules, but separate execution contracts.

## Autonomous behavior boundary

Allowed autonomous behavior:
- discovery
- health probing
- read-only capability inspection
- plan generation
- candidate implementation generation in an isolated workspace
- testing
- static analysis
- contract validation
- staging-only canary when policy allows
- rollback of an explicitly reversible staging action

Approval-required behavior includes:
- new OAuth consent
- secret/API key creation or rotation requiring owner action
- permission elevation
- destructive restore
- production deployment or production mutation
- billing/paid resource creation
- irreversible data mutation
- promotion of self-generated code into trusted production paths

## Durable state model

Recommended durable state families:
- PostgreSQL: authority, manifests, workflow state, grants, leases metadata, approvals, audit indexes
- Redis: bounded cache, locks, rate-limit coordination, ephemeral scheduling support
- Event Store: event history, replay cursors, workflow causation
- Object Storage: large evidence artifacts, reports, immutable bundles
- Vector Store: semantic retrieval artifacts
- Graph Store: capability graph, knowledge graph, topology, dependencies

Durability is selected by semantics; no single storage engine is authority for every state type.

## Autonomy levels

- L0 Manual: human drives every step.
- L1 Assisted: CK plans, human executes.
- L2 Guarded Automation: CK executes reversible/low-risk actions under policy.
- L3 Workflow Autonomy: CK executes multi-step approved workflows with checkpoints and evidence.
- L4 Adaptive Autonomy: CK can replan, fail over, compensate, and discover alternate capabilities.
- L5 Controlled Self-Expansion: CK can propose/build/test/register new candidate capabilities in isolation; human/policy gates promotion.

No level removes Trust Fabric, Evidence Fabric, kill switch, or production approval controls.

## Anti-coupling rules

- Orchestrator MUST NOT import provider-specific SDKs.
- AGNES MUST NOT contain OAuth provider implementations.
- Connectors MUST NOT directly write governance state.
- Providers MUST NOT invoke connectors directly.
- Agents MUST NOT receive raw secrets.
- Event consumers MUST NOT infer authorization from event origin.
- Marketplace packages MUST NOT be trusted solely because they are installed.
- Self-repair MUST NOT modify canonical production code without the normal change/evidence process.

## Target outcome

CK-NEXUS becomes a Universal Autonomous Cognitive Platform where components are selected by capabilities and contracts, connected by typed events, controlled by shared policy/trust, executed through AGNES, and promoted only with verifiable evidence.