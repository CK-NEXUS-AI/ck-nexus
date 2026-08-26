# Universal AI OS Research Delta — 2026-08-27

Baseline: `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
Lifecycle: `DEVELOPMENT_SHADOW`
Production mutation: `false`

This delta records emerging external patterns discovered after the initial capability map. It is research evidence, not adoption authority.

## D-01 Agent Skills Open Format Compatibility

Priority: P1
Status: DISCOVERED / ADAPTER_CANDIDATE

Agent Skills has emerged as a lightweight open folder format centered on `SKILL.md`, with optional scripts, references and assets. CK-NEXUS should support an importer/exporter while preserving stronger CK controls:

- CK signed skill manifest
- declared effects and permissions
- dependency/BOM references
- sandbox tier
- benchmark suite
- source/provenance digest
- policy constraints
- independent verification state

External `SKILL.md` is discovery input only and cannot self-admit into the Capability Registry.

## D-02 MCP Forward-Compatibility Watch

Priority: P0
Status: DISCOVERED / WATCH

The MCP roadmap published 2026-08-22 identifies agentic messaging primitives, HTTP-native transport hardening, agent identity/enterprise security, improved primitives and SDK developer experience as upcoming priorities. CK should implement a version broker and extension registry rather than hard-coding one MCP release.

## D-03 WASI 0.3 Capability Sandbox

Priority: P1
Status: CANDIDATE_ABSENT

WASI 0.3, released 2026-06-11, adds native async (`async func`, `stream<T>`, `future<T>`) to the WebAssembly Component Model. Evaluate Wasmtime/WASI as a lightweight, typed, cross-language execution tier between in-process tools and heavier gVisor/microVM isolation.

Required CK wrapper:
- WIT interface contract
- explicit filesystem/network/clock/random capabilities
- fuel/time/memory limits
- signed component digest
- no ambient credentials
- evidence capture

## D-04 Confidential AI Workload Plane

Priority: P1/P2
Status: CANDIDATE_ABSENT

Confidential Containers currently supports attested confidential workloads across Intel TDX, AMD SEV-SNP and multiple confidential GPU paths. Add an optional confidential execution class for highly sensitive model/data workloads:

`policy -> workload identity -> hardware attestation -> secret release -> execution -> evidence`

Remote hardware attestation does not equal CK production approval; it establishes properties of the execution environment only.

## D-05 Evaluation Standardization via Inspect

Priority: P1
Status: ADAPTER_CANDIDATE

UK AI Security Institute Inspect provides composable datasets, agents, tools, scorers, MCP tooling, sandboxing and tool-call approval plus a large prebuilt evaluation catalog. CK should support an Inspect-compatible evaluation adapter so candidate models/agents/tools can be measured using external and CK-native suites under the same evidence envelope.

## D-06 Memory Architecture Benchmarking

Priority: P1
Status: RESEARCH_REQUIRED

Current agent-memory systems increasingly combine semantic retrieval with entity/graph relations, long-lived agent identity and cross-session state. CK should benchmark, not blindly import, patterns from GraphRAG, Mem0 and Letta.

Required CK memory benchmark dimensions:
- temporal reasoning
- multi-hop retrieval
- cross-session identity
- contradiction/staleness handling
- provenance retention
- deletion/forgetting correctness
- retrieval token cost
- latency
- privacy boundaries

## D-07 Formal Model Checking for Authority Protocols

Priority: P2
Status: CANDIDATE_ABSENT

Use TLA+ plus TLC/Apalache on selected high-value state machines:
- approval lifecycle
- evidence supersession
- distributed idempotency
- capability admission
- production mutation gate
- workflow cancellation/compensation
- credential lease lifecycle

Model-checking output is verification evidence; it cannot replace independent production approval.

## D-08 Physical AI / ROS 2 Adapter Boundary

Priority: P2
Status: CANDIDATE_ABSENT

ROS 2 exposes middleware-independent pub/sub, services, node discovery, QoS and security abstractions. CK should place ROS 2 behind a Physical Action Gateway with simulation-first policy, geofence/safety envelopes, emergency stop and higher approval requirements.

## D-09 Source Authority Hardening

Priority: P0
Status: BLOCKED_GOVERNANCE_CHANGE

The inspected `main` branch currently reports protection disabled and no required status checks. Candidate hardening:
- protected main/ruleset
- required CI + security + verification checks
- review/approval separation
- signed/attested release artifacts
- no force-push for protected refs
- explicit emergency/break-glass path with audit

No configuration change is authorized by this research document.
