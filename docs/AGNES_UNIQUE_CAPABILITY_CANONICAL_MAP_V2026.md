# AGNES / CK-NEXUS Unique Capability Canonical Map V2026

Status: Post-P0 development planning. This map deduplicates capabilities across the active AGNES/CK-NEXUS development PR sets. It does not promote production readiness, Q10/Q11/Q12, or PR #14.

## Canonical rule

A capability has one canonical owner/domain. Shared controls such as CK Governor authority, fail-closed policy, evidence binding, no raw secrets, and production NO-GO are cross-cutting platform invariants and are not counted repeatedly as separate capabilities.

## Unique capabilities by set

### PR #93 — Dual-Track Intelligence Fabric
Canonical domain: cognitive governance / verification

- Evidence-bound Capability Registry with exact-subject binding
- Structured Debate Engine with independent verifier and red-team veto
- Dual-Track Council decision path
- Append-only Evidence Graph lineage
- Self-awareness derived from registered/evidenced capability state
- Deny-by-default Sandbox Runner contract
- Fail-closed Verification Pipeline
- Autonomous Capability Builder state machine
- AGNES role/intelligence pipeline

Do not duplicate: evidence stores, generic councils, or second sandbox authority elsewhere.

### PR #95 — Gen 6.1 Runtime Contracts
Canonical domain: governed interaction runtime

- Governed Computer Use action contract
- Risk/approval/execution-grant model for computer actions
- Durable task/checkpoint/resume/fork contract
- Realtime multimodal session contract
- Ephemeral credential requirement for direct realtime client connections
- Frontier runtime capability taxonomy

Do not duplicate: later UI/browser/mobile work must bind to these execution authorities rather than creating another executor.

### PR #96 — Gen 6.2 Elastic Swarm
Canonical domain: scalable multi-agent execution

- Elastic Swarm Director
- Dynamic Subagent Factory with lifecycle and specialist roles
- Model Pool Selector
- Provider/model fallback and circuit-breaker logic
- Fan-out/Fan-in budget and concurrency controller
- Evidence-backed consensus engine

Do not duplicate: fixed agent catalogs should become profiles for the factory, not parallel agent runtimes.

### PR #97 — Gen 6.3 Cognitive Memory / Learning
Canonical domain: memory lifecycle and skill derivation

- Memory decay / temporal ranking
- Retrieval reinforcement
- Dream consolidation for duplicate merge and supersession while preserving history
- Experience-to-skill candidate derivation
- Memory regression benchmark
- Tenant-isolation checks for memory

Do not duplicate: self-learning modules should emit skill candidates into the same governed promotion path; never auto-install learned skills.

### PR #99 — Gen 6.4 Research + Formal Contracts
Canonical domain: research intelligence and formal evidence

- Bounded iterative Deep Research with source/iteration budgets
- Claim/source Citation Graph using digest-only evidence
- Independent-publisher verification
- Contradiction-dominant claim status
- Hypothesis Tournament with evaluator quorum
- Required dissent and safety-veto dominance
- Evidence-bound evolutionary offspring proposals without auto-activation
- Formal invariant verification receipts with exact-subject and pinned-checker binding
- Reproducible research artifact manifests
- Evaluator-fleet quorum receipts

Do not duplicate: later research agents should use this research/evidence contract rather than inventing another citation or contradiction system.

### PR #102 — Gen 6.5 UI + Multimodal (parallel, not yet integrated into #106 lineage)
Canonical domain: presentation, perception and live steering

- Typed AG-UI-style event/state stream
- Command-vs-event separation: commands request; events mutate visible state
- Typed generative UI component allowlist
- Governed pause/cancel/prioritize/clarify steering
- Typed multimodal attachment envelopes
- Quarantine/trust/sensitivity controls for attachments
- Document layout/OCR result contract with bounding boxes, confidence and pinned extractor receipts
- Media provenance receipts with pinned verifier versions
- Browser/desktop/mobile/realtime UI surface binding to Gen 6.1 authorities

Do not duplicate: arbitrary HTML/JS renderers, second computer executor, or second realtime authority.

### PR #100 — Chat/MCP Bridge V1
Canonical domain: read-only interactive control surface

- Disabled-by-default Chat/MCP bridge
- Governor-approved read-only enablement
- Initial status/memory/swarm/inspect/verify/explain command surface
- Unknown or mutation commands fail closed

Do not duplicate: slash command governance belongs to PR #105; transport/interactive bridge remains here.

### PR #103 — Test Standards V1
Canonical domain: verification infrastructure

- Standard pytest CLI: mock/live provider, attack mode, chaos level
- Standard PolicyViolation and BudgetExceeded exceptions
- A-01..A-05 executable attack-contract tests
- Checkpoint rollback/version-hash guard
- 30-second per-test timeout enforcement in standards CI
- Scoped coverage gate >=80% for governed contracts
- Standard evidence artifacts: test_report.json, attack_trace.log, chaos_trace.log, coverage.xml, junit.xml
- Bounded chaos recovery/disk-full tests
- Lean 4 formal invariant workflow
- Makefile test entry points

Do not duplicate: individual modules should plug into these gates instead of defining their own independent test standards.

### PR #104 — NEXUS-OMNI Resilience & Reliability
Canonical domain: deterministic resilience runtime

- Deterministic adapter-driven fault plans
- Sandbox attestation + execution-grant requirement for chaos dispatch
- Hash-linked append-only JSONL evidence store with fsync
- Canonical deterministic state hashing
- Hash-derived stable choices without mutable global RNG
- Standard vendor-neutral mock provider with success/error/timeout scenarios

Do not duplicate: host-destructive chaos implementations or separate mock contracts.

### PR #105 — NEXUS-OMNI ULTRA Governance
Canonical domain: truthful capability exposure

- Evidence-backed Ultra Capability Registry
- Runtime states: READY_VERIFIED / VERIFIED_NO_EXECUTOR / IMPLEMENTED_UNVERIFIED / SIMULATED / NOT_AVAILABLE / BLOCKED
- Governed slash-command router
- Prompt/persona claims cannot grant runtime authority
- Unverified percentage/module/agent claims are blocked from becoming runtime facts

Do not duplicate: capability truth-state logic in UI, prompt, or provider adapters; all should query the canonical registry.

### PR #106 — Capability-Aware Model Fabric
Canonical domain: intelligence-provider selection

- Provider-neutral model capability taxonomy
- Current/verified/expiring model capability evidence
- Independent/internal/provider evidence source weighting
- Deterministic multi-capability weighted routing
- Minimum capability thresholds with fail-closed routing
- Ordered fallbacks
- Cross-provider independent verifier selection

Do not duplicate: hard-coded vendor winners or separate provider-specific routing logic.

### PR #75 — Connected-Source Intelligence
Canonical domain: governed external knowledge ingestion

- Connected-source inventory across approved mail/drive/repo/database/CRM/dev sources
- Project-relevant minimized signal extraction
- Connector evidence capture
- Untrusted-content/prompt-injection guard for connected content
- Secret exclusion / DLP boundary
- MCP/tool conformance verification
- Read-only remote-device inventory/bridge when an authorized connector actually exists

Do not duplicate: live source discovery in SelfCapabilityManager as fabricated discovery; connected state must come from real connectors.

### PR #86 — MCP 2026 Migration + Supply-Chain Baseline
Canonical domain: protocol modernization and artifact trust

- MCP protocol target 2026-07-28 migration contract
- Header-based method/name routing metadata
- Denial of legacy session/handshake/SSE assumptions under the new profile
- Deterministic non-task list-cache identity
- Digest-only request-parameter evidence projection
- Cosign v3 security baseline contract
- Artifact SHA-256 + certificate identity + HTTPS OIDC issuer requirements
- Standardized bundle-only policy and version floor enforcement

Do not duplicate: create no second MCP server. Upgrade the existing AGNES MCP server through this compatibility contract.

## Consolidated non-duplicate capability domains

1. Cognitive governance and verification
2. Computer-use authority
3. Durable execution
4. Realtime multimodal runtime
5. Elastic multi-agent execution
6. Cognitive memory lifecycle
7. Skill derivation and promotion candidates
8. Deep research and citation/contradiction reasoning
9. Formal verification evidence
10. Typed generative UI and live steering
11. Multimodal attachment/document/media provenance
12. Read-only Chat/MCP control surface
13. Test/eval/security/chaos standards
14. Deterministic resilience runtime
15. Truthful capability governance
16. Evidence-driven model routing
17. Connected-source intelligence and DLP
18. MCP 2026 protocol modernization
19. Software/artifact supply-chain trust

## Build-next capabilities that are genuinely missing or incomplete

These are not duplicates of existing canonical domains and should be developed by extending the owners above:

- A2A 1.0 Gateway + Agent Card Registry
- Agent Skills Registry V2 with portable SKILL.md/package manifests, versioning, signatures and permission scopes
- Durable Execution Engine V2 that persists and executes the existing durable contracts
- Governed Computer Use Executor behind the existing Gen 6.1 policy contract
- Agent Flight Recorder + trace replay bound to the existing Evidence Graph
- Live benchmark/eval ingestion feeding PR #106 model capability evidence
- Memory provenance + contradiction resolver extending Gen 6.3/6.4 rather than creating a second memory store
- Dynamic specialist runtime that executes PR #96 factory records through the existing policy/execution kernel
- Reconcile/integrate PR #102 Gen 6.5 into the main Post-P0 lineage
- Remote Agent Trust / attestation layer for A2A agents
- Digital Twin / production-simulation runtime using PR #104 deterministic fault and evidence primitives

## Anti-duplication architecture

```text
CK GOVERNOR / POLICY / EXECUTION GRANTS
                |
                +-- Capability Truth Registry (#105)
                +-- Evidence / Verification (#93/#103/#104)
                +-- Model Selection (#106)
                +-- Agent Team / Swarm (#96)
                +-- Memory / Learning (#97)
                +-- Research / Formal (#99)
                +-- Computer / Durable / Realtime (#95)
                +-- UI / Multimodal (#102, parallel pending integration)
                +-- Chat/MCP Surface (#100)
                +-- Connected Sources (#75)
                +-- MCP Modernization + Supply Chain (#86)
```

Every future capability should attach to one owner above. New code must not create a competing Governor, Evidence authority, Model Router, Memory Store, Computer Executor, MCP server, or Skill promotion authority.

## Production boundary

This document is a deduplicated development map only. It does not merge any PR, does not promote Q10/Q11/Q12, does not change PR #14, and does not authorize production mutation.
