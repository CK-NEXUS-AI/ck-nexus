# CK-NEXUS Work Queue

> Prioritized implementation queue. A task is DONE only when its acceptance evidence is attached to the exact commit/tree and independently checked.

## P0 — Release and trust baseline

### WQ-001: Finish PR #364 review cycle
- State: CI passed on inspected commit `954c5e6`; Cubic re-review pending; PR remains OPEN / REVIEW_REQUIRED / BLOCKED.
- Scope: resolve only valid review threads, inspect final Cubic feedback, preserve generated-artifact-only workflow writes.
- Acceptance: all required checks pass on latest head; review threads are addressed; PR owner review decision recorded. Do not merge automatically.

### WQ-002: Rebaseline Q10–Q16 against one current candidate
- State: BLOCKED / NOT VERIFIED for current main.
- Scope: calculate exact runtime/deployment subject from current candidate; audit stale evidence; rerun required gates; preserve raw reports and artifact provenance.
- Acceptance: every mandatory gate has exact matching source SHA/tree and subject; independent review completed; release contract authorizes promotion. Production stays NO-GO until then.

### WQ-003: Reconcile stale release documentation
- State: OPEN.
- Scope: compare `RELEASE_STATUS.md`, closure contract, runbooks, evidence JSON and actual current main. Update only when supported by current evidence.
- Acceptance: no stale canonical-main SHA or frozen subject remains presented as current; historical records remain clearly labeled.

## P1 — Agnes execution and persistent context

### WQ-004: Persistent project context packet
- State: IN PROGRESS in this branch.
- Scope: maintain PROJECT_STATE, WORK_QUEUE, AGENT_RUNBOOK, DECISION_LOG, EVIDENCE_INDEX and SESSION_HANDOFF under `docs/operations/`.
- Acceptance: a new session can resume from SESSION_HANDOFF without needing the entire chat transcript; all state claims point to repository evidence or are explicitly labeled as observations.

### WQ-005: Make TeamDirector parallel execution deliberate
- State: PARTIAL / IMPLEMENTED LOCALLY on feat/agnes-persistent-ops-memory-20261110. Existing implementation commits: 6fd0b39690ff92bfeb26789bcd145578cbb0b727 and 501f170be424c0352b5b76b12fb37b49b3a51bb4; reliability-guard changes are currently uncommitted local work.
- Implemented: dependency-wave execution, default per-request concurrency 2 (bounded 1–5), 60-second step timeout, immutable worker snapshots, deterministic result ordering, explicit FAILED/BLOCKED outcomes, shared Agent locks, durable TaskStore idempotency keys with atomic replay/conflict checks, cooperative request cancellation for built-in agents, and a process-wide worker semaphore capped at 2.
- Verification: focused regression 151 passed, 1 existing pytest configuration warning; Ruff, compileall and git diff --check passed. TDD RED→GREEN evidence is recorded under `.superpowers/sdd/2026-11-10-agnes-reliability-guards/`.
- Remaining: MCP adapter integration tests are unverified because the Termux environment lacks the declared `mcp>=1.13,<2` dependency; independent review is pending. Cooperative cancellation cannot forcibly terminate a non-cooperative synchronous Python thread. Global concurrency is per Python process only, not across processes/hosts.
- Scope: continue using existing TeamDirector, ParallelExecutor and ControlPlane; preserve dependency edges and ensure workers do not receive new shell, arbitrary filesystem, network or production authority.
- Acceptance: deterministic dependency-wave tests; concurrency ceiling tests; duplicate-task prevention; cooperative cancellation tests; fail-closed behavior when a dependency fails; MCP adapter verification in a provisioned environment; no production side effects.

### WQ-006: Durable memory adapter
- State: OPEN.
- Scope: design a durable adapter for Unified Memory V2 using the existing SQLite/PostgreSQL patterns. Keep tenant/user isolation, consent, classification, authority ranking, supersession, expiry, deletion/tombstone and provenance.
- Acceptance: restart persistence tests; cross-tenant isolation; explicit-consent tests; secret/regulated rejection; atomic supersession; export/delete tests; migration and backup/restore evidence.
- Constraint: do not enable persistent personal-memory writes by default or persist raw conversations/secrets.

### WQ-007: Agent registry and real execution inventory
- State: OPEN.
- Scope: distinguish role definitions, installed executors, live/healthy agents, and actual task runs. Connect Scout/Architect/Builder/Verifier/Security/Skeptic through the existing registry/control plane where supported.
- Acceptance: status reports separate configured/installed/available/running/verified; every task has correlation ID, bounded lease, owner, allowed paths, result and evidence; Skeptic can block unsupported completion.

## P2 — Developer productization

### WQ-008: Evidence explorer and audit bundle
- State: OPEN.
- Scope: package evidence manifest, source/subject lineage, attestations, test reports, SBOM/license report and offline verification instructions.
- Acceptance: a clean machine can verify the bundle offline; tampering is detected; no secrets included.

### WQ-009: Developer onboarding and clean-room install
- State: OPEN.
- Scope: developer quickstart, configuration reference, supported deployment matrix, example project, API/MCP contract, upgrade/rollback and troubleshooting.
- Acceptance: independent developer completes install, test, sample agent and uninstall/upgrade from documentation only.

### WQ-010: Commercial release package
- State: OPEN; depends on WQ-002, WQ-008 and WQ-009.
- Scope: Free/Pro/White-label packaging, license notices, bill of materials, support boundaries, upgrade policy, release notes and buyer acceptance checklist.
- Acceptance: no Production Ready/Certified claims unless all release gates and buyer acceptance criteria are verified.

## Execution discipline

- Work in bounded slices; parallelize only independent read-only analysis or isolated implementation tasks.
- One Integrator owns merges of worker branches; workers do not edit the same files.
- Every task must define: input SHA, allowed paths, dependencies, expected artifact, test command, risk class, rollback, and evidence location.
- No automatic merge, deployment, purchase, credential change, or destructive cleanup.
