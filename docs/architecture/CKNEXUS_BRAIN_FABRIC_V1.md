# CK-NEXUS Brain Fabric V1

## Purpose

One cognitive entry point over existing CK-NEXUS capabilities. This is a composition layer, not a second authority plane or a new model runtime.

## Components

1. **Core authority** — CK-NEXUS Core/L3 owns identity, policy, permissions, memory authority, execution approval and evidence acceptance.
2. **Planner** — `ControlPlaneOrchestrator` decomposes work into research, implementation, verification and security roles. A plan is not execution.
3. **Work queue** — existing SQLite `TaskStore` provides durable queued work, leases, checkpoints and bounded retries.
4. **Knowledge** — existing rights-gated EPUB/text-PDF ingestion and lexical retrieval. Retrieval is advisory and does not write authoritative memory.
5. **Learning** — `AgentLearningMemory` reads bounded evidence summaries. `BrainJournal` stores task fingerprints and allowlisted metrics, never raw prompts, model outputs or credentials.
6. **Improvement loop** — proposals remain `candidate` until explicit Owner review. No automatic installation, permission grant, merge, deployment or Q10 promotion.
7. **Cloud execution** — GitHub Actions hosted runners are the first offload target for CI, scans, catalog refresh and research jobs. VPS remains the lightweight control plane and secure connector. External services are not connected merely because their SDK or docs exist.

## Cognitive cycle

`Observe → Retrieve → Plan → Route → Execute (authorized worker only) → Verify → Reflect → Propose → Owner review → Adopt`

The first deployable phase supports status, planning, evidence-derived learning, bounded observation journaling and improvement proposals. It does not start autonomous production execution.

## Memory policy

- Store a SHA-256 task fingerprint, bounded reason code, evidence references and numeric allowlisted metrics only.
- Do not store raw prompts, raw model outputs, secrets, regulated data or personal content in the journal.
- A self-reported outcome is never labeled verified.
- Existing explicit-user and system-authority memory rules remain unchanged.

## Cloud-first placement

| Workload | Preferred location | CK-NEXUS responsibility |
|---|---|---|
| CI, tests, security scans | GitHub-hosted Actions runner | Define policy, inspect artifacts and decide whether to accept evidence |
| Long-lived event queue | Hosted queue/database when a connected project is active | Authorize job contracts and validate returned evidence |
| Web/API integration | Provider-hosted API/edge function | Broker identity, scope and result verification |
| Knowledge indexing | Cloud worker when corpus/compute grows | Rights validation, source lineage and retrieval policy |
| Secrets and authority | CK-NEXUS Core / protected secret store | Never send L3 authority to external services |

## Current deployment facts (2026-11-01)

- VPS inspection: 1.9 GiB RAM, 200 MiB immediately free memory, about 6.1 GiB free disk. Heavy frameworks stay off-host.
- GitHub connector is authenticated and lists the user's repositories. Existing repository workflows include a six-hour AI Product Factory schedule and a six-hour preflight schedule. Hosted workflow execution still depends on the relevant branch/workflow being pushed and enabled.
- Vercel connection is visible, Hobby team, zero linked projects; no deployment created.
- Supabase connection exposes one project with status `INACTIVE`; no restoration or migration performed.
- OpenClaw source is available through GitHub but is very large and is not installed on the VPS. Reuse patterns, not the full runtime.
- The user's `agnes-brain` repository was inspected. Safe patterns adapted: thin-client/cloud offload, bounded failover, human-assist queue, search-first, evidence-driven recovery. Unbounded auto-restart, secret harvesting and public unauthenticated tunnels are excluded.

## Acceptance criteria

- Deterministic tests cover privacy, candidate-only promotion, plan-only semantics and authority boundaries.
- Existing test suite remains green.
- MCP exposes brain status, planning, learning context, bounded observations and improvement proposals without granting new execution authority.
- Deployment changes remain limited to the development MCP service; Q10/Q11/Q12 and frozen source remain untouched.
