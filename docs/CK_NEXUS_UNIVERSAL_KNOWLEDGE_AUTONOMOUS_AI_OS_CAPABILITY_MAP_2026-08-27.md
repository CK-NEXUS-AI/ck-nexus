# CK-NEXUS — Universal Knowledge & Autonomous AI Operating System Capability Map

**Thai product name:** ระบบปฏิบัติการปัญญาประดิษฐ์เชิงความรู้และการทำงานอัตโนมัติแบบสากล

**Research snapshot:** 2026-08-27
**Canonical baseline commit:** `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
**Canonical baseline tree:** `25d9c74db2b553667ad085172f8ac7beff4146aa`
**Lifecycle:** Development / Shadow research only
**Production certification:** unchanged / not granted
**Production mutation:** false
**Auto-adoption:** false
**Independent verification required:** true

## Non-negotiable invariants

1. CK-NEXUS remains the authority for state, memory, permissions, policy and execution.
2. Models, agents, protocols and external runtimes are replaceable capability providers, never authority.
3. Discovery is not adoption. `CANDIDATE_ABSENT` means the canonical scan has not established an equivalent implementation; it is not proof of universal absence.
4. No capability may promote itself. Builder/executor and independent verifier must remain distinct.
5. External write, destructive action, merge, deploy and production mutation remain fail-closed until governance requirements are satisfied.
6. Every admitted capability must bind subject, environment, execution identity, evidence and verification result.
7. New capabilities must outperform or materially extend the current baseline before adoption.

## Current source-control boundary observation

At this snapshot the canonical `main` branch reports branch protection disabled and no required status checks. Treat repository ruleset / protected-main hardening as a P0 governance candidate. Do not change repository governance automatically.

## Capability architecture

CK-NEXUS should converge on interoperable planes rather than a monolithic agent framework:

- Cognitive Plane — planning, reasoning, debate, evaluation, learning.
- Knowledge Plane — semantic memory, temporal knowledge, provenance, retrieval, contradiction management.
- Execution Plane — tools, code, browser, desktop, workflows, sandboxes, physical actions.
- Agent Interop Plane — MCP, A2A and capability negotiation.
- Model/Inference Plane — cloud models, local models, distributed inference, model lifecycle.
- Data Plane — contracts, ingestion, CDC, quality, lineage, metadata and impact analysis.
- Identity & Trust Plane — human/device/workload/agent identity, attestation, delegation.
- Policy & Governance Plane — policy-as-code, approvals, risk, proof-carrying actions.
- Evidence & Verification Plane — append-only evidence, independent verification, formal methods and attestations.
- Observability & Evaluation Plane — traces, metrics, quality evaluations, adversarial testing.
- Connectivity Plane — private compute mesh, remote access, service discovery, recovery.
- Supply-Chain Plane — SBOM/ML-BOM, provenance, signing, VEX and license/model/data governance.
- Experience Plane — read-only truth projection, generative UI, accessibility, multilingual interaction.
- Physical/Edge Plane — robotics, sensors, edge autonomy, digital twins and out-of-band recovery.

## P0 — foundation gaps / upgrade candidates

### P0-01 MCP 2026-07-28 Compatibility Layer
Status: `DISCOVERED / UPGRADE_REQUIRED_CANDIDATE`

Add a version-negotiating MCP gateway supporting the 2026-07-28 stateless core, self-describing requests, `server/discover`, `Mcp-Method` / `Mcp-Name` routing, MRTR, cache hints, Tasks extension, MCP Apps extension and hardened authorization. Maintain a compatibility adapter for older MCP servers rather than allowing protocol version drift inside the core.

### P0-02 A2A 1.0 Agent Interoperability Gateway
Status: `CANDIDATE_ABSENT`

Add A2A Agent Cards/capability discovery, version negotiation, task lifecycle, multimodal artifact exchange and cross-vendor agent communication. A2A identities and remote agents remain subordinate to CK authority and policy.

### P0-03 Workload / Agent Identity Fabric
Status: `CANDIDATE_ABSENT`

Add SPIFFE/SPIRE-compatible node and workload attestation, short-lived X.509/JWT SVIDs, automatic rotation and federation. Bind `human_identity`, `device_identity`, `workload_identity`, `agent_identity`, `execution_identity` and `evidence_identity` explicitly.

### P0-04 Policy-as-Code Decision Plane
Status: `CANDIDATE_ABSENT_OR_PARTIAL`

Keep CK policy authoritative while adding an external PDP interface compatible with OPA/Rego and/or Cedar-style policy evaluation. Required features: policy bundles, versioning, simulation, diff, deny-by-default, decision evidence and separation of policy decision from enforcement.

### P0-05 Agent Sandbox Fabric
Status: `CANDIDATE_ABSENT_OR_PARTIAL`

The existing sandbox/cgroup work should gain pluggable isolation tiers: Linux namespaces/cgroups, gVisor, Kata Containers, Firecracker microVM and Kubernetes Agent Sandbox. Admission chooses the minimum sufficient tier from tool risk, source trust, data sensitivity and requested effects.

### P0-06 Durable Cognitive Execution
Status: `CANDIDATE_ABSENT_OR_PARTIAL`

Add Temporal-style durable workflows: event history, deterministic replay, timers, signals, cancellation, human-wait states, sagas/compensation and crash recovery for multi-hour/day/month agent workflows. AGNES task provenance and durable execution history must remain separate but cross-linked.

### P0-07 Sovereign Private AI Compute Fabric
Status: `CANDIDATE_ABSENT`

Add a transport abstraction for Tailscale, Headscale and native WireGuard; governed SSH; private service discovery; local model endpoints; node enrollment; cryptographic node admission; remote recovery; and offline/degraded operation.

### P0-08 Distributed Local Inference Control Plane
Status: `CANDIDATE_ABSENT`

Extend model routing into system-level inference scheduling: vLLM/SGLang/TensorRT-LLM/llama.cpp/Ollama adapters, distributed workers, prefill/decode disaggregation, KV-cache-aware routing, KV offload, topology awareness, autoscaling, GPU/VRAM/thermal/power awareness and heterogeneous device scheduling. NVIDIA Dynamo/Ray Serve LLM are reference implementations, not mandatory authorities.

### P0-09 Enterprise Data Contract Registry
Status: `CANDIDATE_ABSENT`

Support Open Data Contract Standard-compatible dataset contracts covering structure, semantics, quality, ownership, SLA/freshness/retention and server location. Contract changes require compatibility and consumer-impact analysis.

### P0-10 Data Lineage + Impact Graph
Status: `CANDIDATE_ABSENT`

Support OpenLineage-compatible Run/Job/Dataset events and column-level lineage. Connect data lineage to CK execution/evidence provenance without conflating them.

### P0-11 CDC / Streaming Data Fabric
Status: `CANDIDATE_ABSENT`

Add database-log/stream connectors for PostgreSQL, MySQL, MSSQL, MongoDB and event systems, with Debezium-style CDC semantics, schema-change handling, replay checkpoints, deduplication and evidence-bound ingestion.

### P0-12 Data Quality Evidence Gate
Status: `CANDIDATE_ABSENT_OR_PARTIAL`

Add executable quality assertions, schema/integrity/business-rule/freshness checks, statistical drift detection and quality evidence bound to dataset version/contract/run.

### P0-13 Source-to-Target / System Analyst Compiler
Status: `CANDIDATE_ABSENT`

Compile requirements and source-to-target mappings into typed intermediate representations that can generate schema, transformation specs, API contracts, lineage, tests, documentation, UAT cases and evidence requirements.

### P0-14 Protected Source Authority / Repository Ruleset
Status: `BLOCKED_GOVERNANCE_CHANGE`

Introduce protected `main`, required CI/security/verification checks, signed or attested releases, review separation and explicit merge authority. This must be configured by authorized governance, not by capability discovery.

## P1 — trust, observability and ecosystem interoperability

### P1-01 OpenTelemetry GenAI / Agent Trace Model
Unify CK events with standard traces, metrics and logs; propagate trace context across model calls, MCP, A2A, workflows, tools, browser/desktop execution and data pipelines. Sensitive prompts/tool arguments remain opt-in/redacted.

### P1-02 Proof-Carrying Action Envelope
Every high-risk action proposal should carry subject, actor/workload identity, requested effects, policy decision, approvals, evidence digests, expiry and replay/idempotency key. Executors reject incomplete proofs.

### P1-03 Typed Effect / Capability Security
Declare tool effects such as READ, WRITE, NETWORK, SECRET, EXECUTE, DESTRUCTIVE, MONEY, PHYSICAL and PRODUCTION_MUTATION. Scheduler and policy reason over effects before choosing an executor.

### P1-04 Software/AI Supply-Chain Attestation
Support SLSA v1.2 provenance, in-toto attestations and Sigstore/Cosign-style identity-bound signing. Verify artifact, source, builder and policy before capability admission.

### P1-05 SBOM / ML-BOM / CBOM / VEX Registry
Use CycloneDX-compatible BOMs for software, models, datasets, cryptography, hardware/operations and vulnerability exploitability. Generate an `Agent BOM` linking model, tools, skills, runtime, datasets and policies.

### P1-06 Event Contract Registry
Support CloudEvents envelopes, AsyncAPI event contracts, JSON Schema/Protobuf/Avro schema registration, compatibility checks and contract-driven test generation.

### P1-07 Model Intelligence Registry
Track context limits, modalities, tool support, structured-output reliability, benchmark scores, safety constraints, cost, latency, locality, quantization, license and hardware requirements per model/version.

### P1-08 Model / Skill / Tool Benchmark Arena
Create repeatable benchmark suites and canary/shadow comparisons. Include task success, correctness, tool accuracy, latency, cost, safety, recovery and evidence completeness.

### P1-09 Agent Evaluation Harness
Integrate reference evaluation patterns from Inspect AI plus domain benchmarks such as SWE-bench, browser/computer-use benchmarks and custom CK enterprise workflows. Benchmark output cannot self-promote a capability.

### P1-10 Adversarial / Chaos Agent Lab
Inject provider outages, network partitions, malformed tool output, prompt injection, poisoned memory, credential denial, timeouts, rate limits, corrupted state and sandbox escape attempts.

### P1-11 Temporal Knowledge Graph
Add entity resolution, time-valid facts, event/causal links, bitemporal state, contradiction detection, source provenance and explicit supersession. GraphRAG-style retrieval should be optional and evidence-aware.

### P1-12 Memory Lifecycle / Forgetting Policy
Separate working, episodic, semantic, procedural and personal memory; implement retention, consolidation, confidence decay, deletion/privacy requests and stale-memory invalidation.

### P1-13 Context Budget Manager
Allocate context tokens among invariant policy, task state, retrieved evidence, memory, tool results and conversational history; add semantic compression, cache-aware planning and source-preserving summarization.

### P1-14 Enterprise System Catalog
Create a Backstage-like internal catalog for systems, services, APIs, datasets, pipelines, agents, models, tools, owners, SLAs, deployments and evidence — projected from authoritative registries rather than manual dashboard state.

### P1-15 Progressive Delivery / OpenFeature Adapter
Feature/model/tool/skill/policy rollout should support shadow, 1%, 5%, 25%, 50%, 100% stages governed by evaluation and rollback evidence.

### P1-16 Secrets/KMS/HSM Expansion
Extend the current credential broker with OIDC workload federation, dynamic secrets, external KMS/HSM, secret lease/TTL, automatic rotation and cryptographic-use evidence without logging secret material.

## P2 — universal autonomy and physical/digital operation

### P2-01 Browser Execution Fabric
Sandboxed browser sessions with DOM/network/screenshot evidence, deterministic action traces, download quarantine, prompt-injection detection and policy-bound uploads/submissions.

### P2-02 Desktop / Computer-Use Runtime
Governed mouse/keyboard/window/terminal automation with accessibility-tree grounding, action previews, interruption, replay and human takeover.

### P2-03 Multimodal Realtime Plane
Streaming audio, speech, image/video, sensor and realtime model sessions with timestamp alignment and evidence identities; WebRTC-compatible transport where appropriate.

### P2-04 Robotics / Physical AI Bridge
ROS 2 / Open-RMF style adapters; device capability discovery; geofencing; safety envelopes; dead-man switch; simulation-before-physical-action; mandatory higher governance for physical mutation.

### P2-05 Digital Twin / Simulation Fabric
Represent servers, networks, data pipelines, workflows, business processes and robots in simulators before risky changes. Enable counterfactual plans and rollback rehearsal.

### P2-06 Out-of-Band Hardware Recovery
Governed Wake-on-LAN, Redfish/IPMI, PiKVM, UPS and smart-power integrations for nodes that cannot be recovered through SSH/Tailscale alone.

### P2-07 Offline / Edge Autonomous Mode
Local policy cache, local model fallback, CRDT/event reconciliation candidates, bounded offline authority, delayed evidence upload and conflict reconciliation after reconnect.

### P2-08 Federated / Privacy-Preserving Learning
Research federated learning, secure aggregation and privacy-preserving adaptation. Never enable model training on personal/enterprise data by default.

### P2-09 Scientific Experiment Runtime
Experiment plans, notebook/compute sandbox, dataset/model versioning, hypothesis/result ledger, reproducibility manifests and instrument/simulator adapters.

### P2-10 Formal Verification Plane
Use TLA+/Apalache/Alloy for critical protocols and state machines; use proof assistants such as Lean only for selected high-value invariants. Machine-checked results become evidence, not unilateral production approval.

### P2-11 Runtime Safety Shields
Add invariant monitors around autonomous loops: action budget, scope budget, time budget, tool-call budget, network egress budget, money budget and physical-risk budget.

### P2-12 Human Collaboration / Approval Inbox
Unified high-risk decision queue with risk preview, diff, evidence, affected assets, compensation plan, verifier identity and explicit expiry.

## P3 — product, enterprise and learning expansion

### P3-01 BPMN/DMN + Process Mining Bridge
Import/export business processes and decision rules, discover actual process variants from event logs, compare designed vs observed workflows and propose automations.

### P3-02 Requirement-to-Evidence Traceability Graph
`Requirement -> Business Rule -> Design -> API/Schema -> Code -> Test -> Evidence -> Release` with automatic gap and impact analysis.

### P3-03 Architecture / Dependency Graph Compiler
Build service/module/data/tool dependency graphs from source, infrastructure, APIs and runtime telemetry; support blast-radius analysis before change.

### P3-04 License / Model / Dataset Usage Governance
Track OSS licenses, model licenses, dataset terms, allowed commercial use, redistribution and jurisdictional constraints.

### P3-05 Synthetic Data / Scenario Generator
Produce privacy-safe fixtures, rare failure scenarios, simulated enterprise transactions and adversarial examples for tests; tag all synthetic artifacts explicitly.

### P3-06 Skill Package Standard
Signed skill manifests declaring inputs/outputs/effects/dependencies/models/tools/policies/tests/benchmarks. Unknown skills enter quarantine and capability admission.

### P3-07 Capability Marketplace / Federation
Federate capability registries between CK installations without transferring authority. Import is discovery-only until local security/benchmark/verification/owner gates pass.

### P3-08 Multi-tenant Sovereign Workspace
Tenant-isolated identity, policy, memory, data, tools, models, evidence, encryption domains, budgets and audit logs.

### P3-09 Accessibility & Universal Interaction
WCAG-oriented interfaces, keyboard/screen-reader operation, voice alternatives, multilingual semantics, locale/timezone/unit normalization and Thai-first quality tests.

### P3-10 Generative UI / MCP Apps Projection
Allow agents/tools to propose dynamic UI artifacts while preserving presentation-only semantics: generated UI never becomes source authority and cannot bypass policy.

## P4 — frontier research, not baseline dependency

- World-model / environment-model integration.
- Neuromorphic / specialized accelerator adapters.
- Homomorphic-encryption inference and secure MPC where cost is justified.
- Zero-knowledge proofs for selected execution/identity properties.
- Swarm/self-organizing scheduling under explicit governance.
- Automated theorem synthesis for CK invariants.
- Continual-learning research with replay/forgetting controls.
- Cross-device personal knowledge federation with selective disclosure.
- Energy/carbon-aware inference scheduling.
- Autonomous architecture search and self-optimization under shadow-only evaluation.

## Reference standards / projects checked in this research cycle

- Model Context Protocol specification `2026-07-28`
- Agent2Agent Protocol `1.0.0`
- SPIFFE / SPIRE
- Open Policy Agent / Rego
- Kubernetes SIG Agent Sandbox
- gVisor, Kata Containers, Firecracker
- Temporal durable execution
- NVIDIA Dynamo, Ray Serve LLM, vLLM ecosystem
- Open Data Contract Standard
- OpenLineage
- Debezium-style CDC
- OpenTelemetry semantic conventions
- SLSA `1.2`, in-toto, Sigstore
- CycloneDX `1.7`
- CloudEvents, AsyncAPI, OpenFeature
- formal-method candidates: TLA+, Apalache, Alloy, Lean
- robotics/physical-AI candidates: ROS 2, Open-RMF and simulation-first runtimes

## Admission protocol for every candidate

`DISCOVER -> NORMALIZE -> DUPLICATE/ABSENCE CHECK -> THREAT MODEL -> SANDBOX -> BENCHMARK -> EVIDENCE -> INDEPENDENT VERIFY -> OWNER/GOVERNOR APPROVAL -> ADOPT -> CANARY/SHADOW -> REVERIFY`

A failed or incomplete stage is fail-closed. No candidate in this document is production-certified merely by being listed.

## Initial implementation sequence

1. Reconcile existing MCP implementation against MCP 2026-07-28.
2. Define canonical Agent/Workload/Execution Identity schema and SPIFFE adapter contract.
3. Define A2A gateway contract behind CK Authority.
4. Define pluggable Sandbox Runtime Interface and evaluate gVisor / Agent Sandbox / Firecracker tiers.
5. Add Durable Workflow contract separate from AGNES provenance.
6. Add Private Compute Node descriptor and Local/Distributed Inference registry.
7. Add Data Contract + OpenLineage schemas before activating CDC ingestion.
8. Add OTel GenAI/agent trace mapping and standard evaluation envelope.
9. Add supply-chain BOM/attestation schemas.
10. Run independent verification before any adoption or production claim.
