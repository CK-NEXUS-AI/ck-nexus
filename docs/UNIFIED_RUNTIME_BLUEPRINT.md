# CK-NEXUS Unified Runtime Blueprint

## From Prototype -> Authority -> Autonomous Platform

**Core rule:** UI, Agent, and Model are never the source of truth by themselves.  
All authority must flow through **Runtime + Policy + Verification + Evidence**.

If a result has no evidence, it is not a pass.

---

## 1. Operating Thesis

CK-NEXUS should evolve as one coherent runtime, not as a pile of disconnected apps, agents, or prompts.

The system must answer four questions before it acts:

1. What is the intent?
2. Who or what is authorized to execute it?
3. What contract governs the action?
4. What evidence will prove the result?

That leads to the canonical control chain:

```text
Intent
→ Context
→ Task DAG
→ Capability Resolution
→ Policy + Authority + Risk + Cost
→ Credential Lease
→ Execute
→ Verify
→ Evidence
→ Commit Durable State
→ Emit Event
→ Trigger Next Task
```

---

## 2. Layer Model

### 2.1 Experience Plane

User-facing surfaces are presentation layers only.

- Sales Portal
- Buyer Portal
- Dashboard
- Chat Interface
- Command Center
- Admin / Control Views

Responsibilities:

- render current state from backend
- show verified capability and health status
- surface evidence and release posture
- never invent authority

### 2.2 Control Plane

This is the system governor.

- Universal Registry
- Capability Registry
- Provider Registry
- Connector Registry
- Skill Registry
- Workflow Registry
- Policy Engine
- Identity and Trust
- Event Bus
- Discovery Engine

Responsibilities:

- register entities
- discover entities
- resolve implementations
- enforce policy
- bind identity and approvals
- govern budgets and grants

### 2.3 Cognitive Plane

This plane reasons, but does not own permission.

- Intent Graph
- Context Engine
- Planner
- Task DAG
- Capability Graph
- Model Router
- Tool Router
- Agent Router
- Critic
- Consensus
- Risk Evaluator
- Memory
- Knowledge Graph
- Graph RAG

Responsibilities:

- decide what should happen next
- select candidate implementations
- produce plans and critiques
- never bypass policy or executor

### 2.4 Integration Fabric

This plane connects CK-NEXUS to the outside world.

- MCP
- A2A
- OAuth
- REST
- Webhooks
- GitHub
- Gmail
- Drive
- Slack
- Databases
- n8n

Responsibilities:

- normalize external systems into contracts
- expose capabilities through registry metadata
- keep credential handling centralized
- support read-only, write, and high-risk classifications

### 2.5 AGNES Execution Plane

This plane performs the action.

- Dispatcher
- Capability Check
- Commit-time Authorization
- Credential Lease
- Idempotency
- Sandbox / Connector / Provider
- Retry / Failover / Recovery

Responsibilities:

- execute only approved work
- acquire and release credentials by lease
- preserve idempotency and replay safety
- isolate side effects
- recover safely on failure

### 2.6 Verification Plane

This plane decides whether execution actually succeeded.

- Result Verification
- Side-effect Verification
- Security Verification
- False-completion Detection

Responsibilities:

- verify the effect, not just the log
- detect stale, partial, or fabricated completion
- fail closed when proof is missing

### 2.7 Evidence Fabric

This plane records the truth.

- Runtime Evidence
- Audit Ledger
- Provenance
- Attestation
- Acceptance
- Release Gates

Responsibilities:

- retain durable proof
- chain evidence to subject and run
- support release gating
- make status auditable over time

### 2.8 Data Plane

Durable system state lives here.

- PostgreSQL
- Redis
- Vector store
- Graph store
- Object store
- Queue
- Event store

Responsibilities:

- keep state durable
- keep event history recoverable
- separate transient runtime from durable evidence

---

## 3. Universal Registry

The central abstraction is the **Universal Registry**.

It stores and resolves:

- Provider
- Connector
- Agent
- Skill
- Workflow
- Prompt
- Policy
- Schema
- Dataset

### 3.1 Registry contract

Every module should expose the same metadata shape:

```yaml
id: connector.github
kind: connector
version: 1.0.0

capabilities:
  - repo.read
  - repo.search
  - issue.create
  - pull_request.create

contracts:
  input: schemas/github-request.json
  output: schemas/github-result.json

risk:
  repo.read: READ_ONLY
  issue.create: MEDIUM
  pull_request.create: HIGH

auth:
  schemes: [github_app, oauth2]

events:
  emits:
    - github.issue.created
    - github.pr.created

health:
  probe: /health
```

### 3.2 Registry API

Canonical API order:

1. `register`
2. `discover`
3. `resolve`
4. `health`
5. `execute(metadata only)`

Important:

- metadata can describe capability
- metadata cannot grant permission
- execution must still pass policy and verification

### 3.3 Registry rules

- Everything is a capability
- Everything has a contract
- Everything is discoverable
- Everything is policy-controlled
- Everything risky is approval-aware
- Everything important produces evidence
- Everything stateful is durable
- Everything observable has trace and health
- Everything replaceable is plugin-based

---

## 4. Canonical Authority Chain

### 4.1 What owns authority

Authority belongs to the runtime system that can:

- authenticate
- authorize
- lease credentials
- execute work
- verify results
- emit evidence

### 4.2 What does not own authority

These are never truth sources by themselves:

- UI
- model output
- agent output
- chat text
- prompt text
- local simulation

### 4.3 Authority rule

- UI is never authority
- Model never owns permission
- Agent never bypasses executor
- No evidence = no pass

---

## 5. Workflow Contract

The main runtime flow should always be:

```text
USER / APP / CHAT / API / EVENT
        ↓
EXPERIENCE PLANE
        ↓
CONTROL PLANE
        ↓
COGNITIVE PLANE
        ↓
INTEGRATION FABRIC
        ↓
AGNES EXECUTION PLANE
        ↓
VERIFICATION PLANE
        ↓
EVIDENCE FABRIC
        ↓
DATA PLANE
```

Or in task form:

```text
Intent
→ Context
→ Task DAG
→ Capability Resolution
→ Select Agent / Model / Skill / Connector
→ Policy + Authority + Risk + Cost
→ Credential Lease
→ Execute
→ Verify
→ Evidence
→ Commit Durable State
→ Emit Event
→ Trigger Next Task
```

The important distinction is:

- planning is advisory
- execution is controlled
- verification is authoritative
- evidence is durable

---

## 6. Manifests and Contracts

Every module should carry one manifest format.

### 6.1 Minimum manifest fields

```yaml
id:
kind:
version:
capabilities:
contracts:
permissions:
risk:
cost:
health:
events:
metadata:
```

### 6.2 Manifest semantics

- `id` identifies the module
- `kind` says what it is
- `version` makes it replaceable
- `capabilities` describe what it can do
- `contracts` define input/output expectations
- `permissions` define authority boundaries
- `risk` defines approval requirements
- `cost` defines resource impact
- `health` defines live probing
- `events` define emitted signals
- `metadata` provides extra discovery context

### 6.3 Contract policy

If a module is missing:

- contract
- health
- risk classification
- evidence binding

then it is not production-authoritative.

---

## 7. Self-Expansion Model

Self-expansion is allowed only through controlled growth.

### 7.1 Expansion flow

```text
Capability Gap
→ Search Existing Plugin
→ Found?
→ Install Candidate
→ Generate Proposal
→ Isolated Workspace
→ Build
→ Tests
→ Security Scan
→ Evidence
→ Human Approval
→ Canary
→ Promote
```

### 7.2 Non-negotiable rule

Do not modify production core directly when a gap is discovered.

Instead:

1. detect the gap
2. search existing plugins or modules first
3. propose the change
4. build in isolation
5. verify
6. produce evidence
7. require approval
8. canary
9. promote

### 7.3 Promotion rule

- no evidence, no promotion
- no approval, no promotion
- no canary success, no promotion
- no contract test, no promotion

---

## 8. UI Binding Rules

UI must be backend-driven.

### 8.1 Dashboard

Dashboard should read:

- `/health`
- `/capabilities`
- `/evidence`
- `/connectors`

### 8.2 Connector Hub

Show only real backend state:

- registered connectors
- discovery results
- schema verification
- health
- authorization state

### 8.3 Sales Page

Sales claims must be generated from evidence registry or release identity, not from static marketing text.

### 8.4 Buyer Portal

Buyer Portal should display only capabilities verified for the current environment.

UI must never become the authority layer.

---

## 9. Repo Target Shape

Recommended repo topology:

```text
platform/
  control_plane/
  capability_fabric/
  event_fabric/
  connection_fabric/
  trust_fabric/
  evidence_fabric/

providers/
integrations/
agnes/
intelligence/
automation/
```

### 9.1 Placement intent

- `platform/control_plane` owns identity, registry, policy, and authority
- `platform/capability_fabric` owns capability resolution and contracts
- `platform/event_fabric` owns durable event flow
- `platform/connection_fabric` owns connector adapters and transport
- `platform/trust_fabric` owns grants, risk, approvals, and leases
- `platform/evidence_fabric` owns provenance and release-gate truth
- `providers` holds model/provider adapters
- `integrations` holds external service adapters
- `agnes` holds execution and autonomous workflow logic
- `intelligence` holds planning, reasoning, and routing
- `automation` holds self-expansion and operational workflows

---

## 10. Suggested Build Order

The highest-value build order is:

1. Registry + manifest schema
2. Capability resolver
3. Event bus
4. Policy / authority binding
5. AGNES execution binding
6. Evidence API
7. Connector runtime
8. Multi-AI provider fabric
9. Dashboard runtime binding
10. Self-expansion pipeline
11. Marketplace
12. SDK
13. Ecosystem layer

This sequence matters because control must exist before scale.

---

## 11. Prototype -> Authority -> Autonomous Platform

### 11.1 Prototype

Goal:

- prove the UI and workflow concept
- show demo behavior
- keep scope narrow

Signals:

- simulation is acceptable only for prototype surfaces
- no production authority
- no autonomous mutation

### 11.2 Authority

Goal:

- backend becomes the source of truth
- registry and evidence are real
- policy and verification govern execution

Signals:

- backend-driven UI
- verified connectors
- durable evidence
- explicit approval gates

### 11.3 Autonomous Platform

Goal:

- the system can safely expand capability
- new capabilities are discovered, verified, and promoted through a controlled path

Signals:

- capability discovery
- plugin-based expansion
- contract verification
- evidence-backed promotion
- no direct core bypass

---

## 12. Governance Invariants

Lock these in as permanent rules:

- Everything is a Capability
- Everything has a Contract
- Everything is Discoverable
- Everything communicates through Events
- Everything is Policy-controlled
- Everything risky is Approval-aware
- Everything important produces Evidence
- Everything stateful is Durable
- Everything observable has Trace/Health
- Everything replaceable is Plugin-based
- UI never becomes Authority
- Model never owns Permission
- Agent never bypasses Executor
- No Evidence = No PASS

---

## 13. Mapping to Current CK-NEXUS Components

This blueprint should align with existing repo concepts:

- `creator_app/connector_fabric/*` -> capability and connector fabric
- `creator_app/agnes/execution/*` -> execution plane
- `creator_app/observability.py` -> evidence and trace support
- `creator_app/health.py` -> health surface
- `creator_app/council_authority/*` -> trust and approval boundary
- `creator_app/provider_router.py` -> model/provider routing
- `creator_app/api.py` -> experience plane entrypoint
- `evidence/*.json` -> evidence fabric
- `docs/R28_UNIVERSAL_AUTO_CONNECTOR_FABRIC.md` -> connector rule set
- `docs/DEVELOPMENT_COUNCIL.md` -> advisory cognitive layer

---

## 14. Practical Reading Order

If someone is joining the repo for the first time, read in this order:

1. this blueprint
2. `docs/ARCHITECTURE.md`
3. `docs/DEVELOPMENT_COUNCIL.md`
4. `docs/R28_UNIVERSAL_AUTO_CONNECTOR_FABRIC.md`
5. `docs/PROTOTYPE_TO_AUTHORITY_ROADMAP.md`
6. `docs/AGNES_CAPABILITY_MAP.md`
7. `docs/BUILD_BRIEF.md`
8. the relevant implementation modules

---

## 15. Final Rule

CK-NEXUS only progresses when runtime, policy, verification, and evidence agree.

If the UI says yes but the evidence says no, the answer is no.

If the model says yes but policy says no, the answer is no.

If the agent says yes but executor or verification says no, the answer is no.

That is the platform.
