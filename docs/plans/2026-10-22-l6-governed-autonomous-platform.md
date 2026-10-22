# CK-NEXUS L6 Governed Autonomous Platform Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Advance CK-NEXUS toward a free-first, restart-safe 24/7 AI engineering platform and stop only when L6 acceptance gates are proven.

**Architecture:** Reuse the existing MCP, Control Plane, AI Team, execution kernel, sandbox, verifier, provider registry, and evidence paths. Add a durable local queue/checkpoint layer first, then a bounded worker supervised by systemd, then governed proposal-to-promotion flow. The worker must not invoke paid or unknown-cost providers unless an operator-configured policy proves the selected route is free and within quota.

**Tech Stack:** Existing Python 3.12 virtualenv, SQLite, pytest, Ruff, systemd, existing CK-NEXUS MCP and agent components.

## Global Constraints

- Work directly in `/root/ck-nexus`; preserve the existing dirty working tree and uncommitted changes.
- Reuse installed tools and dependencies. Do not install duplicate agent frameworks.
- Never print, copy into evidence, or commit API keys, OAuth tokens, or other credentials.
- Do not expose the loopback-only MCP endpoint to the public Internet.
- Free-only means no unverified paid model calls, paid hosted services, or quota bypasses. When free quota cannot be confirmed, pause model-dependent work and continue local checks only.
- Use bounded task execution, retry ceilings, leases, checkpoints, rate limits, kill switch, audit events, and explicit security gates.
- Do not delete source, user data, failed-test logs, or evidence. Remove only temporary files proven disposable.
- Do not promote code to production solely because tests pass; require verification, security review, evidence, and the configured approval policy.

---

## Verified baseline (2026-10-22)

- `/root/ck-nexus` exists and has many uncommitted modifications; do not reset, clean, or overwrite unrelated work.
- Disk: approximately 3.9 GB available on `/` at last check.
- Services `cknexus-api-gateway.service`, `cknexus-scanner.service`, `cknexus-watchdog.timer`, and `cknexus-mcp.service` reported active.
- The current Control Plane builds a bounded four-role graph, but planning defaults to `PLANNED_NOT_EXECUTED`; it is not itself a continuously running worker.
- Existing full-suite evidence before this change: 743 passed, 2 skipped, 1 deprecation warning.
- New durable queue/checkpoint store was added in `creator_app/control_plane/task_store.py`; focused Control Plane tests pass.

## L1 — Infrastructure Layer

- [ ] Verify restart policy, watchdog coverage, disk thresholds, and health checks for the actual deployed runtime.
- [ ] Confirm persistent state location and permissions for the service account before enabling any new daemon.
- [ ] Acceptance: service health is observable, restart recovery is demonstrated, and disk/permission failures produce actionable evidence.

## L2 — Tool Execution Layer

- [ ] Inventory the installed CLI, MCP tools, sandbox, and filesystem/terminal access; mark each available, authenticated, and tested separately.
- [ ] Add a policy adapter that allows only verified tools and enforces read-only defaults, command timeouts, and output redaction.
- [ ] Acceptance: contract tests prove denied actions stay denied and secret-like values are redacted.

## L3 — AI Agent Layer

- [ ] Validate each existing provider's authentication, model availability, quota/cost status, and timeout behavior without exposing credentials.
- [ ] Add provider routing with free-only eligibility, deadlines, circuit breakers, and fallback only to providers meeting the same cost policy.
- [ ] Acceptance: tests prove unknown-cost or exhausted providers are skipped and local non-model work remains available.

## L4 — Multi-Agent Orchestration

- [ ] Connect the durable queue to a bounded worker using existing TeamDirector/ParallelExecutor; persist claim, stage checkpoint, attempts, and outcome.
- [ ] Configure a systemd service only after the deployed source path, service-account permissions, free-provider policy, and kill switch are verified.
- [ ] Acceptance: enqueue → claim → checkpoint → restart/lease recovery → completion is demonstrated from real logs without duplicate claims.

## L5 — Autonomous Engineering

- [ ] Route code changes into an isolated workspace/worktree and require focused tests, relevant integration tests, lint, and security checks.
- [ ] Record patch hashes, test outputs, review outcomes, and provenance in evidence.
- [ ] Acceptance: a failed test or security check blocks promotion; source changes are never silently applied to production.

## L6 — Governed Self-Improving Platform

- [ ] Add proposal review, versioned policy, owner/approver boundaries, rollback, and tamper-evident evidence links.
- [ ] Allow automated promotion only for explicitly policy-approved low-risk changes; require human approval for credentials, public exposure, production data, permissions, billing, and destructive operations.
- [ ] Bound self-improvement with budget limits, queue limits, retry ceilings, stop conditions, and a kill switch.
- [ ] Acceptance: demonstrate the complete loop—observe → propose → isolate → test → security review → authorize → promote/rollback—with evidence and a restart-safe audit trail.

## Current implementation deliverable

- [x] Add SQLite-backed task persistence with atomic claims, leases, checkpoint writes, result/error capture, and expired-lease recovery.
- [x] Add tests for restart persistence, expired-lease requeue, duplicate IDs, and competing store instances.
- [ ] Integrate the store into a long-running worker and prove systemd recovery.
- [ ] Validate free-only provider routing before enabling background model calls.

The platform is **not yet certified L6** until every acceptance gate above has test or runtime evidence. A working queue is a foundation, not proof of 24/7 autonomous operation.
