# CK-NEXUS Prototype -> Authority -> Autonomous Platform Roadmap

Status: guidance document for implementation sequencing

## Decision

Do not build `brain.py` as a standalone source of truth.

Treat the AI-CK Core Brain idea as a **prototype narrative** that must be absorbed into the existing CK-NEXUS runtime:

- UI is presentation only
- Model is advisory only
- Agent is execution-bound only
- Runtime + Policy + Verification + Evidence remain authoritative

If a proposal has no evidence, it does not become a platform decision.

---

## 1. What the pasted brain concept actually contributes

The submitted concept is useful as a **capability-shaping prototype**:

- Researcher: external source gathering
- Architect: structure and contracts
- Evaluator: scoring and critique
- Coder: bounded generation of scaffolding
- Tester: retry and validation loop
- LangGraph: workflow control
- OpenRouter/free providers: low-cost model access
- FastAPI wrapper: integration surface

But none of those should become the source of truth on their own.

The correct placement is:

- research and drafting in the cognitive plane
- execution in AGNES
- state and authority in control/evidence planes
- UI as a consumer of backend truth

---

## 2. Phase plan

### Phase 0 - Prototype ingestion

Goal:

- absorb the idea into CK-NEXUS terminology
- keep it as a prototype, not production authority
- map its agents to existing plane boundaries

Deliverables:

- model of the 5 agent roles
- workflow sketch
- evidence requirements
- no standalone `brain.py` authority path

### Phase 1 - Registry and manifest foundation

Goal:

- make every provider, connector, skill, workflow, and prompt discoverable
- normalize metadata into a single registry contract

Deliverables:

- universal registry schema
- manifest format
- capability classification
- health and contract metadata

### Phase 2 - Capability resolution

Goal:

- stop asking "which model?"
- start asking "which capability is needed?"

Deliverables:

- capability resolver
- model/tool/agent routing rules
- risk and cost metadata
- policy checks before resolution

### Phase 3 - Execution binding

Goal:

- bind planning to actual execution paths
- ensure credentials are leased, not exposed

Deliverables:

- AGNES execution binding
- credential lease flow
- idempotency support
- sandbox/connector/provider adapters

### Phase 4 - Verification and evidence

Goal:

- verify outcomes, side effects, and completion claims
- record proofs in durable evidence

Deliverables:

- verification API
- false-completion detection
- evidence ledger
- release-gate integration

### Phase 5 - UI runtime binding

Goal:

- make dashboard/buyer/sales surfaces read from backend truth
- remove simulation as the authority layer

Deliverables:

- backend-driven dashboard
- live connector hub
- evidence-aware sales claims
- buyer portal showing only verified capability

### Phase 6 - Controlled self-expansion

Goal:

- let AGNES propose capability growth
- require plugin discovery, isolated build, tests, security scan, evidence, approval, and canary before promote

Deliverables:

- capability gap detection
- plugin search first
- isolated workspace proposal
- evidence-backed promotion path

---

## 3. What to do with free model providers

The prototype mentions OpenRouter and other free or low-cost providers. In CK-NEXUS, that belongs in the provider fabric only.

Rules:

- provider lists are discovery data, not authority
- free-tier availability is volatile
- a model being available does not make it production-approved
- routing changes need policy, evidence, and approval

If a provider is used, it must flow through:

`Capability -> Policy -> Credential Lease -> Execution -> Verification -> Evidence`

---

## 4. Recommended implementation order

1. Registry + manifest schema
2. Capability resolver
3. Policy / authority binding
4. AGNES execution binding
5. Evidence API
6. Connector runtime
7. Provider fabric
8. Dashboard runtime binding
9. Self-expansion pipeline

This order is preferred because it establishes control before scale.

---

## 5. Explicit non-goals

- no standalone brain service as source of truth
- no agent-owned permission model
- no model-driven UI truth
- no silent auto-promotion from prototype to authority
- no production claim without evidence

---

## 6. Acceptance rule

The prototype only matters if it can be translated into a contract, executed under policy, verified, and recorded as evidence.

Everything else is inspiration, not implementation.
