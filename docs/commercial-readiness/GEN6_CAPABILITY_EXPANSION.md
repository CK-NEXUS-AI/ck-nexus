# CK-NEXUS / AGNES Gen 6 Capability Expansion

Status: POST-P0 DEVELOPMENT ONLY

This document turns current frontier-agent capabilities into CK-NEXUS adapter/contracts without transferring authority to any provider or external framework.

## Confirmed capability signals

### OpenAI Responses / agent runtime
Current official platform material confirms background Responses, context management/compaction, hosted shell/container execution, MCP, skills, computer-use surfaces, and typed/structured tool calls. CK should model these as provider capabilities, never as direct authority.

### Gemini Computer Use
Current Gemini Computer Use documentation supports browser/mobile/desktop environments, screenshot-to-action loops, action intents, configurable safety policies, and optional screenshot prompt-injection detection. CK must place Policy + Approval + Evidence between suggestion and execution.

### Durable execution
LangGraph documents durable execution with checkpointing, persistence, streaming, and human-in-the-loop as first-class runtime behavior. CK should implement a provider-neutral DurableTask contract rather than adopt LangGraph as the authority layer.

### Memory evolution
Mem0 documents opt-in Memory Decay using access-history reinforcement and bounded recency weighting at search time. CK Memory 3.0 should implement a provider-neutral temporal ranking/reinforcement contract while preserving append-only supersession history.

### AG-UI
AG-UI documents streaming, shared state snapshots/deltas, frontend tool calls, interrupts, subagents, steering, tool-output streaming, typed attachments, and generative UI building blocks. CK should validate declarative UI against an allowlisted component schema before rendering.

### MCP 2026-07-28
The current MCP revision has a stateless protocol core, optional server/discover, Mcp-Method/Mcp-Name routing, cacheable list responses, authorization hardening, extension framework, and deprecation policy. CK needs dual-version migration, capability identity binding, cache-scope policy, and issuer binding.

### A2A
Current A2A specifications support Agent Card-based discovery, long-running task streaming/subscription, push-notification capabilities and newer v1.0 Agent Card/interface evolution. CK should treat A2A as an interoperability adapter only.

## Gen 6 capability taxonomy

Perception: IMAGE_UNDERSTANDING, VIDEO_UNDERSTANDING, SCREEN_UNDERSTANDING, OCR, DOCUMENT_LAYOUT, REALTIME_AUDIO, REALTIME_VIDEO, SPATIAL_REASONING.

Action: COMPUTER_USE, BROWSER_USE, DESKTOP_USE, MOBILE_USE, SHELL, CODE_EXECUTION, TOOL_USE.

Durability: DURABLE_TASK, BACKGROUND_TASK, CHECKPOINT, RESUME, FORK, REWIND, TIME_TRAVEL.

Team intelligence: MULTI_AGENT, SUBAGENT, SWARM, MODEL_POOL, REVIEWER, FAN_OUT, FAN_IN.

Memory: MEMORY_READ, MEMORY_WRITE, MEMORY_DECAY, MEMORY_REINFORCEMENT, MEMORY_CONSOLIDATION, PROCEDURAL_MEMORY.

Research/science: DEEP_RESEARCH, CITATION_GRAPH, SCIENCE, FORMAL_PROOF, HPC, SIMULATION, EVOLUTIONARY_SEARCH.

UI/interoperability: GENERATIVE_UI, AG_UI, MCP, A2A, FRONTEND_TOOL_CALL.

Trust: PROMPT_INJECTION_DETECTION, MEDIA_PROVENANCE, SAFETY_JUDGE, POLICY_REEVALUATION, EXECUTION_ATTESTATION.

## Implementation waves

### Gen 6.1 — Action + Durability
Build provider-neutral contracts for Computer Use, background tasks, checkpoint/resume/fork, context compaction, and programmatic tool plans. No host-level direct execution is allowed from the model layer.

### Gen 6.2 — Elastic Team Intelligence
Add task complexity analysis, parallelizability estimation, dynamic subagent creation, model-pool assignment, fan-out/fan-in budgets, reviewer/challenger separation, and cost-per-success scoring.

### Gen 6.3 — Memory 3.0
Add temporal ranking, reinforcement, background consolidation, duplicate merge, contradiction detection, supersession, procedural skill extraction, and benchmark suites.

### Gen 6.4 — Research + Formal Intelligence
Add iterative research-gap detection, claim-level citation verification, citation graph, hypothesis/evaluator tournament, reproducibility artifacts, and optional proof adapters for machine-checkable invariants.

### Gen 6.5 — Generative UI + Multimodal
Add AG-UI-compatible event/state adapter, typed declarative UI schema, live steering, multimodal attachments, OCR/document structure and media provenance verification.

### Gen 6.6 — World / Physical Intelligence
Add digital-twin and scenario-simulation contracts first. Physical/robot actions remain blocked until simulate-before-act, explicit physical-action grants, isolation and independent verification are proven.

## Dual-Track integration

Track B Researcher/Scout discovers candidate providers, libraries, protocols and implementation patterns. All unknown code is quarantined and pinned to source/version/license before evaluation.

Track A Architect/Builder/Updater implements provider-neutral contracts and adapters. Verifier + Red Team independently test security, policy, provenance, cost and failure behavior.

Council decisions are limited to REJECT, RESEARCH_ONLY, LOCAL_EVALUATE, IMPLEMENT_POST_P0 or ELIGIBLE_FOR_PROMOTION_REVIEW. No council decision can directly mark a production gate PASS.

## Claims that must not be encoded without primary-source verification

Model names/aliases, benchmark scores, GitHub star counts, maximum subagent counts, maximum tool-call counts, regulatory obligations, provider pricing and framework major-version claims are volatile. They belong in the Research Evidence layer with source/date/version, not as hard-coded architecture facts.

## Production boundary

This Gen 6 work is not Q10, Q11 or Q12 evidence. PR #14 remains untouched. No production promotion is allowed until canonical production closure passes independently.
