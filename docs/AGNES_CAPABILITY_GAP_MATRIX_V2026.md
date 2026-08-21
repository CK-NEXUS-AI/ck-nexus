# AGNES Capability Gap Matrix V2026

Status: Post-P0 development audit only. This document does not change Q10/Q11/Q12, PR #14, or production authority.

Audit base: `028fe49b54c426ead937b359578930428c8f3cac` (`post-p0/capability-aware-model-fabric-v1`).

## Status vocabulary

- **HAVE** — capability exists in the audited branch with executable or testable development behavior.
- **PARTIAL** — meaningful contracts/components exist, but a required runtime/executor/protocol surface is missing.
- **PARALLEL_NOT_INTEGRATED** — capability exists in another open development PR but is not in the audited branch.
- **MISSING** — no implementation was found in the audited branch.
- **DUPLICATE** — a proposed capability would repeat an existing authority/runtime and should be integrated instead of rebuilt.
- **BUILD_NEXT** — recommended next development target.

Percentages are engineering-readiness estimates for the audited development scope, not production-readiness claims.

## Executive matrix

| # | Capability | Status | Dev readiness | Evidence in audited/parallel code | Main gap | Recommendation |
|---|---|---|---:|---|---|---|
| 1 | A2A 1.0 Gateway + Agent Card Registry | **MISSING / BUILD_NEXT** | **5%** | No A2A/Agent Card implementation found in audited branch | No remote-agent identity, capability discovery, delegated task envelope, trust/policy gateway | Build provider-neutral A2A contract first; no remote mutation authority |
| 2 | MCP 2026-07-28 Runtime Adapter | **PARTIAL / BUILD_NEXT** | **50%** | `creator_app/agnes/mcp_server.py` provides real loopback Streamable HTTP, `stateless_http=True`, JSON response, governed tools | No explicit 2026-07-28 protocol-version contract, header routing policy, Tasks/MCP Apps/EMA extensions, migration tests | Upgrade existing MCP authority; do not create a second MCP server |
| 3 | Durable Execution V2 | **PARTIAL / BUILD_NEXT** | **60%** | `durable_runtime.py`, durable JSONL persistence, checkpoint guard, crash-recovery and disk-full chaos tests | No durable scheduler/orchestrator, retry policy engine, resumable node executor, replay/fork coordinator | Extend current durable contracts into one crash-safe execution runtime |
| 4 | Computer Use Runtime Executor | **PARTIAL / BUILD_NEXT** | **40%** | `computer_use_contract.py` has browser/desktop/mobile proposal, screenshot digest, injection-scan evidence, risk and execution-grant policy | No perception adapter, accessibility-tree target resolver, browser/desktop/mobile executor, post-action verifier | Build executor behind existing policy; never bypass `ComputerUsePolicy` |
| 5 | Agent Skills Registry V2 | **PARTIAL / BUILD_NEXT** | **30%** | `self_capability_manager.py` declares plugin/skill system and capability inventory | No portable `SKILL.md` package contract, lazy loading, dependency/version/signature/permission/evidence manifest | Introduce signed/versioned skill packages and map legacy capability declarations into them |
| 6 | Agent Flight Recorder + Replay | **PARTIAL / BUILD_NEXT** | **45%** | `evidence_graph.py`, hash-linked evidence store, test artifacts and event/evidence concepts exist | No unified run trace, model/tool spans, cost/latency accounting, replay index, failure taxonomy | Build one append-only run ledger connected to Task/Run/Node/Agent/Tool/Evidence IDs |
| 7 | Live Benchmark/Eval Feed for Model Fabric | **PARTIAL / BUILD_NEXT** | **65%** | `model_capability_evidence.py` + `capability_aware_model_router.py` support verified/expiring evidence, weighted routing, provider-diverse verifier | Evidence ingestion is manual/static; no scheduled benchmark collector, normalization provenance or drift detection | Build ingestion + expiry/revalidation pipeline; keep routing provider-neutral |
| 8 | Memory Provenance + Contradiction Resolver | **PARTIAL / BUILD_NEXT** | **60%** | memory decay, dream consolidation, experience-to-skill promotion and memory regression tests exist | No explicit contradiction graph, source precedence, memory edit/supersession workflow, per-memory provenance chain | Add contradiction detection/resolution and bind every durable memory to evidence lineage |
| 9 | Dynamic Specialist Factory + Verifier Council | **HAVE/PARTIAL** | **75%** | `dynamic_subagent_factory.py` has typed specialist lifecycle; swarm budget and capability-aware model routing support bounded dispatch and cross-provider verifier selection | Factory creates records, not a full live spawn/execute/retire runtime; verifier orchestration is not one end-to-end service | Integrate factory + budget + router + verification pipeline instead of adding more fixed agents |
| 10 | MCP Apps / Generative UI Bridge | **PARALLEL_NOT_INTEGRATED** | **45% current branch / ~70% parallel contract** | PR #102 has `ag_ui_contract.py`, typed components/events/steering, attachments, UI surface binding; file is absent from audited #106 branch | Parallel branch not reconciled; no MCP Apps server-rendered runtime/executor | Reconcile PR #102 concepts into current development lineage, then add MCP Apps adapter |
| 11 | Remote Agent Trust / Reputation Layer | **MISSING / BUILD_NEXT** | **10%** | Existing governance/evidence can be reused | No remote-agent identity attestation, trust score, capability proof, revocation/quarantine registry | Build after A2A contract; trust must derive from evidence, not self-claims |
| 12 | Digital Twin / Simulation Runtime | **PARTIAL / BUILD_NEXT** | **35%** | Deterministic state, standard mocks, governed chaos and simulation tests provide primitives | No production-like topology/state twin, scenario model, replayable external-service simulators, promotion gate from simulation result | Build deterministic simulation graph on top of existing mock/chaos/evidence primitives |

## Development readiness summary

Simple average across the 12 audited frontier capabilities: **43.8%**.

This number intentionally penalizes missing interoperability/runtime surfaces. It should not be confused with the much higher CI readiness of individual Post-P0 PRs already implemented and tested.

### By layer

- **Governance / policy foundations:** ~85%
- **Evidence / deterministic test foundations:** ~80%
- **Model routing / evaluation contracts:** ~65%
- **Multi-agent local orchestration contracts:** ~70%
- **Durable autonomy runtime:** ~60%
- **Computer-use execution runtime:** ~40%
- **Portable skills runtime:** ~30%
- **Inter-agent interoperability (A2A):** ~5%
- **Remote-agent trust:** ~10%
- **Digital-twin simulation:** ~35%
- **Generative UI in current #106 lineage:** ~45% because the richer Gen 6.5 work is still parallel/unintegrated

## What CK-NEXUS should NOT rebuild

1. **Do not create a second MCP authority.** Upgrade `creator_app/agnes/mcp_server.py` to the 2026 protocol contract.
2. **Do not create a second Computer Use policy.** Add executors behind `ComputerUsePolicy`.
3. **Do not create another generic evidence system.** Unify `EvidenceGraph`, hash-linked evidence, CI artifacts and run/event IDs into one Flight Recorder.
4. **Do not add dozens of hard-coded agents.** Extend `DynamicSubagentFactory` + budget + model router into on-demand specialists.
5. **Do not hard-code model winners.** Continue using verified, expiring capability evidence.
6. **Do not promote parallel UI contracts as integrated.** Reconcile PR #102 explicitly before claiming the current line has Gen 6.5 UI runtime.

## Recommended build order

### Wave A — Interoperability core

1. **A2A Gateway + Agent Card Registry**
2. **MCP 2026-07-28 Adapter**
3. **Agent Skills Registry V2**

Reason: these three define how AGNES discovers, loads and communicates with capabilities without vendor lock-in.

### Wave B — Durable autonomous execution

4. **Durable Execution V2**
5. **Computer Use Runtime Executor**
6. **Agent Flight Recorder + Replay**

Reason: AGNES needs crash-safe execution and evidence before more autonomy is enabled.

### Wave C — Intelligence quality

7. **Live Benchmark/Eval Feed**
8. **Memory Provenance + Contradiction Resolver**
9. **Dynamic Specialist Runtime + Verifier Council integration**

Reason: improve decisions with fresh evidence and reduce provider/model monoculture.

### Wave D — Interaction and simulation

10. **Reconcile Gen 6.5 UI/Multimodal into current lineage + MCP Apps bridge**
11. **Remote Agent Trust/Reputation Layer**
12. **Digital Twin / Simulation Runtime**

Reason: these depend on the interoperability, evidence and durable-execution primitives above.

## External 2026 design signals used for prioritization

- MCP 2026-07-28 moves to a stateless core and adds header-based routing, cacheable lists, authorization hardening, a formal extensions framework and Tasks; MCP Apps is part of the extension direction.
- Agent Skills is an open portable pattern based on a `SKILL.md` plus scripts/resources that agents can discover and load dynamically.
- A2A is an open Linux Foundation protocol for secure agent-to-agent interoperability across vendors/frameworks.

These external signals are architecture inputs only. They do not become CK-NEXUS authority until implemented, tested and evidence-bound in the repository.

## Production boundary

All percentages and recommendations above are Post-P0 development planning data. They do not change Production `NO-GO`, do not promote Q10/Q11/Q12, and do not authorize merge/deploy/external mutation.
