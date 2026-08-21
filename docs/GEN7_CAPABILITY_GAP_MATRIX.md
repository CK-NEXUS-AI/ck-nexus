# CK-NEXUS Gen 7 Capability Gap Matrix

Baseline: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`

> Development architecture inventory only. This document does not change Q10/Q11/Q12, release subject identity, or Production NO-GO.

## Authority rules

- CK-NEXUS remains authority for state, permissions, policy, execution, verification, and evidence.
- Models/agents/providers are replaceable intelligence workers and cannot self-authorize.
- `DISCOVERED != CONNECTED != AUTHORIZED != EXECUTED != VERIFIED != PRODUCTION_APPROVED`.
- Unknown tools/connectors/skills enter quarantine and fail closed.
- Raw secrets are never exposed to browser UI or agents; credentials are brokered/scoped.

## Status summary

| Status | Count |
|---|---:|
| EXISTS | 0 |
| PARTIAL | 18 |
| CONTRACT_ONLY | 2 |
| MISSING | 10 |
| EXPERIMENTAL | 0 |

## 8 Gen 7 Fabrics

| Fabric | Primary streams | Scope |
|---|---|---|
| Identity & Delegated Access | AIO-17 / AIO-23 | registration, consent, delegated scopes, tenant/workspace |
| Universal Connection | AIO-20 | OAuth/OIDC, API, MCP, OpenAPI, web/plugin/device connectors |
| Capability & Skill | AIO-22 | graph, skill packages, foundry, passports, reputation |
| Intelligence | AIO-22 | router, model arena, council, composition |
| Research & Perception | AIO-20 | search federation, swarm, multimodal perception |
| Execution | AIO-16 / AIO-21 | durable runs, sandbox, computer use, devices, simulation |
| Knowledge & Context | AIO-18 | memory, temporal truth, contradictions, context compiler |
| Governance & Evidence | AIO-17 / AIO-19 | policy, approval, verification, event/evidence chain |

## Capability matrix

| # | Capability | Fabric | Stream | Status | Priority | Risk |
|---:|---|---|---|---|---|---|
| 1 | Universal Computer-Use Fabric | Execution | AIO-21 | MISSING | P0 | HIGH |
| 2 | Managed Agent Sandbox Runtime | Execution | AIO-21 | PARTIAL | P0 | HIGH |
| 3 | Long-Horizon / Durable Agent Runtime | Core | AIO-16 | PARTIAL | P0 | HIGH |
| 4 | Research Swarm / Deep Research Fabric | Research | AIO-20 | PARTIAL | P0 | MEDIUM |
| 5 | Search Federation Engine | Research | AIO-20 | PARTIAL | P0/P1 | MEDIUM |
| 6 | MCP 2026 Runtime Upgrade | Connection | AIO-20 | PARTIAL | P0 | HIGH |
| 7 | Secure Elicitation Runtime | Identity | AIO-17 | CONTRACT_ONLY | P0 | HIGH |
| 8 | Portable Skill Runtime / Skill Store | Capability | AIO-22 | PARTIAL | P0/P1 | HIGH |
| 9 | Skill Auto-Discovery + Skill Compiler | Capability | AIO-22 | PARTIAL | P1 | HIGH |
| 10 | Capability Graph | Capability | AIO-22 | PARTIAL | P1 | MEDIUM |
| 11 | Automatic Model Capability Benchmarking | Intelligence | AIO-22 | MISSING | P1 | MEDIUM |
| 12 | Dynamic Model Composition | Intelligence | AIO-22 | PARTIAL | P1 | MEDIUM |
| 13 | Formal Verification Layer | Governance | AIO-17 | MISSING | P1 | HIGH |
| 14 | World Model / Simulation Fabric | Execution | AIO-21 | MISSING | P1/P2 | HIGH |
| 15 | Embodied AI / Robotics Fabric | Execution | AIO-21 | MISSING | P2 | CRITICAL |
| 16 | Multi-Robot / Multi-Device Swarm | Execution | AIO-21 | MISSING | P2 | CRITICAL |
| 17 | Perception Fabric | Research | AIO-20 | PARTIAL | P1 | MEDIUM |
| 18 | Real-time Multimodal Runtime | Core | AIO-16 | MISSING | P1 | HIGH |
| 19 | Agent Self-Evaluation / Reflection | Governance | AIO-17 | PARTIAL | P1 | MEDIUM |
| 20 | Contradiction Engine | Knowledge | AIO-18 | MISSING | P1 | MEDIUM |
| 21 | Temporal Knowledge / Truth Timeline | Knowledge | AIO-18 | PARTIAL | P1 | MEDIUM |
| 22 | Active Memory Management | Knowledge | AIO-18 | PARTIAL | P1 | HIGH |
| 23 | Context Compiler | Knowledge | AIO-18 | MISSING | P1 | HIGH |
| 24 | Agent Identity / Capability Passport | Capability | AIO-23 | PARTIAL | P1 | HIGH |
| 25 | Zero-Trust Tool Reputation System | Governance | AIO-17 | PARTIAL | P1 | HIGH |
| 26 | Dynamic Approval UX | Identity | AIO-19 | PARTIAL | P1 | HIGH |
| 27 | Generative UI Runtime | UI | AIO-19 | CONTRACT_ONLY | P1 | MEDIUM |
| 28 | Cognitive UI Event Bus | UI | AIO-19 | PARTIAL | P0/P1 | HIGH |
| 29 | Artifact-Native Operating System | Core | AIO-16 | PARTIAL | P1 | MEDIUM |
| 30 | Scientific Agent Fabric | Research | AIO-20 | MISSING | P2 | HIGH |

## Implementation / acceptance detail

### 1. Universal Computer-Use Fabric — MISSING

- Stream: `AIO-21`
- Dependencies: sandbox, policy, approval
- Implementation path: Browser/Desktop/Android/Shell drivers behind Governor; every mutating action policy-gated
- Acceptance: simulated browser action denied/approved correctly; evidence sealed

### 2. Managed Agent Sandbox Runtime — PARTIAL

- Stream: `AIO-21`
- Dependencies: AGNES sandbox, workspace, policy
- Implementation path: Generalize existing sandbox to portable executor contract
- Acceptance: same task executes in local sandbox and alternate executor with identical result envelope

### 3. Long-Horizon / Durable Agent Runtime — PARTIAL

- Stream: `AIO-16`
- Dependencies: run state, idempotency, evidence
- Implementation path: Add checkpoint/pause/resume/retry/fork/replay/migrate state machine
- Acceptance: kill/restart runtime and resume exact run without duplicate side effects

### 4. Research Swarm / Deep Research Fabric — PARTIAL

- Stream: `AIO-20`
- Dependencies: AGNES, connector fabric, evidence
- Implementation path: Director + scouts + contradiction/source verifier over normalized evidence
- Acceptance: multi-source research produces deduped claims and evidence graph

### 5. Search Federation Engine — PARTIAL

- Stream: `AIO-20`
- Dependencies: connector fabric, OpenAPI/MCP
- Implementation path: Normalized search adapters and source scoring
- Acceptance: same query fans out to >=3 adapters and returns normalized ranked results

### 6. MCP 2026 Runtime Upgrade — PARTIAL

- Stream: `AIO-20`
- Dependencies: connector_fabric/mcp.py, governance
- Implementation path: Capability negotiation, task mapping, subscriptions, auth hardening, untrusted descriptions
- Acceptance: malicious MCP metadata cannot gain undeclared capability; task/subscription tests pass

### 7. Secure Elicitation Runtime — CONTRACT_ONLY

- Stream: `AIO-17`
- Dependencies: Credential Broker, approval
- Implementation path: Form vs secure URL/OAuth elicitation; secrets never requested in normal form
- Acceptance: secret field request is rejected and replaced by brokered auth flow

### 8. Portable Skill Runtime / Skill Store — PARTIAL

- Stream: `AIO-22`
- Dependencies: AGNES skills, capability registry
- Implementation path: Signed/versioned skill package with permissions, tests, SBOM
- Acceptance: install signed skill in quarantine; permission mismatch blocks execution

### 9. Skill Auto-Discovery + Skill Compiler — PARTIAL

- Stream: `AIO-22`
- Dependencies: agnes_discovery, skills, sandbox
- Implementation path: Discover→quarantine→manifest→test→scan→score→review→register
- Acceptance: unknown skill remains unusable until sandbox tests and approval pass

### 10. Capability Graph — PARTIAL

- Stream: `AIO-22`
- Dependencies: capability registry, provider metadata
- Implementation path: Replace flat capability lists with dependency/trust graph
- Acceptance: planner resolves multi-capability task to valid model+tool+verifier chain

### 11. Automatic Model Capability Benchmarking — MISSING

- Stream: `AIO-22`
- Dependencies: provider router, evidence
- Implementation path: Evidence-driven model arena for quality/latency/cost/tool accuracy
- Acceptance: router choice changes only after benchmark evidence revision

### 12. Dynamic Model Composition — PARTIAL

- Stream: `AIO-22`
- Dependencies: provider router, council
- Implementation path: Planner/research/coder/verifier composition and consensus modes
- Acceptance: multi-model run records per-worker result and deterministic judge decision

### 13. Formal Verification Layer — MISSING

- Stream: `AIO-17`
- Dependencies: policy engine, evidence
- Implementation path: Lean/SMT/Z3 adapter for selected invariants; LLM verdict never authoritative
- Acceptance: critical invariant violation blocks execution even when model says safe

### 14. World Model / Simulation Fabric — MISSING

- Stream: `AIO-21`
- Dependencies: planner, policy, verifier
- Implementation path: Counterfactual/simulation stage before high-risk execution
- Acceptance: deployment proposal produces predicted impact and deny/allow evidence before mutation

### 15. Embodied AI / Robotics Fabric — MISSING

- Stream: `AIO-21`
- Dependencies: capability graph, safety gate
- Implementation path: Robot/IoT adapter contract; AGNES never direct motor authority
- Acceptance: unsafe actuator command denied by safety boundary in simulator

### 16. Multi-Robot / Multi-Device Swarm — MISSING

- Stream: `AIO-21`
- Dependencies: device identity, capability graph
- Implementation path: Common node contract for device/robot/compute swarm
- Acceptance: scheduler selects only online trusted nodes within risk ceiling

### 17. Perception Fabric — PARTIAL

- Stream: `AIO-20`
- Dependencies: vision/audio/document support
- Implementation path: Normalize text/image/video/audio/screen/DOM/spatial/telemetry observations
- Acceptance: mixed-media task yields typed observations with provenance

### 18. Real-time Multimodal Runtime — MISSING

- Stream: `AIO-16`
- Dependencies: event bus, perception, provider fabric
- Implementation path: Unified realtime stream for voice/camera/screen/tool events
- Acceptance: session preserves ordering/correlation across concurrent modalities

### 19. Agent Self-Evaluation / Reflection — PARTIAL

- Stream: `AIO-17`
- Dependencies: verification, council
- Implementation path: Actor self-check + critic + independent verifier; self-check no authority
- Acceptance: actor success with verifier failure remains blocked

### 20. Contradiction Engine — MISSING

- Stream: `AIO-18`
- Dependencies: evidence graph, research
- Implementation path: Claim relation SUPPORT/CONTRADICT/PARTIAL/UNKNOWN
- Acceptance: conflicting sources remain explicit and synthesis reports disagreement

### 21. Temporal Knowledge / Truth Timeline — PARTIAL

- Stream: `AIO-18`
- Dependencies: supersession/evidence concepts
- Implementation path: valid_from/until, observed_at, supersedes relations for knowledge
- Acceptance: stale fact is superseded without deleting history

### 22. Active Memory Management — PARTIAL

- Stream: `AIO-18`
- Dependencies: memory modules, evidence
- Implementation path: Working/episodic/semantic/procedural/project/evidence memory lifecycle
- Acceptance: forget/expire/supersede operations obey policy and audit trail

### 23. Context Compiler — MISSING

- Stream: `AIO-18`
- Dependencies: memory, policy, skills
- Implementation path: Compile minimum sufficient policy+memory+skill+state context
- Acceptance: irrelevant/stale memory excluded; required policy always included

### 24. Agent Identity / Capability Passport — PARTIAL

- Stream: `AIO-23`
- Dependencies: agent registry, permissions
- Implementation path: Machine-readable identity/version/skills/permissions/risk/trust/eval
- Acceptance: passport hash change invalidates prior trust attestation

### 25. Zero-Trust Tool Reputation System — PARTIAL

- Stream: `AIO-17`
- Dependencies: connector risk, sandbox, evidence
- Implementation path: UNKNOWN→QUARANTINED→SCANNED→SANDBOXED→VERIFIED→TRUSTED lifecycle
- Acceptance: schema/publisher/binary change automatically downgrades trust

### 26. Dynamic Approval UX — PARTIAL

- Stream: `AIO-19`
- Dependencies: approval runtime, adaptive UI
- Implementation path: Explain action/reason/impact/recovery/risk/scope; allow once/task/modify/deny
- Acceptance: high-risk request cannot execute before explicit scoped approval

### 27. Generative UI Runtime — CONTRACT_ONLY

- Stream: `AIO-19`
- Dependencies: adaptive UI, schemas
- Implementation path: Validated UI intent schema for tables/charts/maps/timeline/diff/form/artifact
- Acceptance: untrusted UI schema cannot inject scripts or exceed allowed component set

### 28. Cognitive UI Event Bus — PARTIAL

- Stream: `AIO-19`
- Dependencies: event signals, evidence
- Implementation path: Single backend event envelope drives UI state and evidence
- Acceptance: UI changes only after authoritative event; correlation chain verified

### 29. Artifact-Native Operating System — PARTIAL

- Stream: `AIO-16`
- Dependencies: artifact/evidence concepts
- Implementation path: Typed artifact lifecycle with lineage, revision, verification, publish
- Acceptance: artifact digest/revision lineage remains reproducible across rerun

### 30. Scientific Agent Fabric — MISSING

- Stream: `AIO-20`
- Dependencies: research, sandbox, artifacts
- Implementation path: Literature/hypothesis/experiment/data/statistics/reproduction workbench
- Acceptance: research result includes reproducible notebook/artifacts/citation verification

## Build order

1. P0 connection/security substrate: Secure Elicitation, MCP VNext, sandbox portability, durable state.
2. P0 execution/research: Computer Use, Search Federation, Research Swarm, authoritative Event Bus.
3. P1 capability intelligence: Capability Graph, Skill Runtime/Foundry, Model Arena/Composition.
4. P1 knowledge/governance: Temporal Truth, Context Compiler, Contradictions, Tool Reputation, Formal Verifier.
5. P1 UI/artifacts: Dynamic Approval UX, Generative UI, artifact lineage.
6. P2 simulation/physical/science: World Model, Robotics, device swarm, Scientific Agent Fabric.

## Non-goals

- Do not promise literal connectivity to every website on the internet.
- Do not bypass provider consent, OAuth, API terms, or human approval boundaries.
- Do not give AGNES direct mutation authority.
- Do not treat connector discovery as authorization.
- Do not merge this development inventory into a production release until normal evidence gates pass.
