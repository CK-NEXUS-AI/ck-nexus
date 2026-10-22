# MCP Task Queue Integration Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the hardened CK-NEXUS TaskStore through the existing loopback-only MCP service as a bounded durable task-lifecycle interface without model calls, shell execution, or production mutation.

**Architecture:** Add a thin MCP adapter over `creator_app/control_plane/task_store.py`; keep lease, retry, persistence, and fencing rules in TaskStore. Store service state under a service-owned local state directory, preserve the existing authenticated/loopback MCP boundary, and deploy only the reviewed adapter plus required control-plane files into `/opt/cknexus-mcp` with backup and rollback.

**Tech Stack:** Python, FastAPI/MCP server already used by CK-NEXUS, SQLite, pytest, Ruff, systemd, Desktop Commander.

## Global Constraints

- Work directly in `/root/ck-nexus`; preserve unrelated dirty work and do not reset, clean, rebase, merge, or push.
- Do not call hosted inference, model APIs, or external AI providers.
- Do not store API keys, credentials, lease tokens, or private keys in task payloads, checkpoints, status output, logs, or evidence.
- MCP remains bound to `127.0.0.1:8765` and its existing authentication/resource validation remains unchanged.
- Queue completion is workflow state only; it is never release verification and never authorizes production mutation.
- MCP task tools must not run shell commands, apply patches, commit code, deploy arbitrary files, restart services, or mutate production.
- Task input/checkpoint/result sizes and lease duration must remain bounded by explicit constants.
- Deployment uses targeted file backup, SHA-256 capture, service-user ownership checks, focused live tests, restart of only `cknexus-mcp.service`, post-deploy canaries, and exact-file rollback on failure.
- No destructive disk cleanup is part of this implementation.

---

### Task 1: Harden and contract the MCP TaskStore adapter

**Files:**
- Modify: `creator_app/agnes/mcp_server.py` at existing MCP tool registration/handler sections
- Modify: `creator_app/control_plane/task_store.py` only when adapter-facing behavior needs a narrowly scoped correction
- Test: `tests/test_control_plane_mcp.py`

**Interfaces:**
- Consumes: `TaskStore.enqueue`, `TaskStore.claim_next`, `TaskStore.save_checkpoint`, `TaskStore.finish`, `TaskStore.get`, existing MCP registration and auth context.
- Produces: `cknexus_task_enqueue(job_id, description, priority=2, context="")`; `cknexus_task_claim(worker_id, lease_seconds=300)`; `cknexus_task_checkpoint(job_id, worker_id, lease_token, checkpoint)`; `cknexus_task_finish(job_id, worker_id, lease_token, success, result=None, error=None)`; `cknexus_task_status(job_id)`.

- [ ] **Step 1: Add focused failing tests**

Test the five tool contracts with an isolated temporary SQLite database: enqueue/claim/checkpoint/finish/status happy path; duplicate job; empty queue; expired lease; stale lease-token rejection; status excludes lease token; invalid lease duration; bounded payload size; secret-shaped payload rejection; and confirmation that the adapter performs no external/network/model calls.

- [ ] **Step 2: Verify the relevant failure**

Run: `.venv/bin/python -m pytest -q tests/test_control_plane_mcp.py`
Expected: the new task-tool tests fail because the MCP task tools are not yet registered/implemented.

- [ ] **Step 3: Implement the minimum behavior**

Add one thin adapter per tool. Resolve the database path from `CKNEXUS_TASK_DB` when configured, otherwise the service user's `~/.local/state/cknexus/control-plane.sqlite3`. Ensure the parent state directory and SQLite file are service-user-owned and mode 0700/0600 respectively. Validate only the explicitly bounded interface fields: identifiers, priority range, lease duration, and configured maximum serialized payload sizes. Reject secret-shaped keys/values as defense-in-depth and return stable sanitized error codes without raw tracebacks. Never return lease tokens from status. Keep the existing MCP auth and loopback configuration untouched.

- [ ] **Step 4: Verify the focused pass**

Run: `.venv/bin/python -m pytest -q tests/test_control_plane_mcp.py`
Expected: all task-tool contract tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `.venv/bin/python -m pytest -q tests/test_control_plane_task_store.py tests/test_control_plane_integration.py tests/test_control_plane_verification.py`
Expected: all focused Control Plane tests pass with no new failure.

- [ ] **Step 6: Commit the passing deliverable**

Do not create a Git commit automatically because the repository is already intentionally dirty and the user has not requested commits. Preserve the working tree for the next deployment task.

### Task 2: Verify repository-wide behavior and prepare a deployment bundle

**Files:**
- Modify: `docs/plans/2026-10-22-phase-abc-hardening-report.md` only to record verified queue integration results
- Create: `progress.md` at repository root for execution ledger
- Test: repository test/lint/compile commands

**Interfaces:**
- Consumes: Task 1 MCP adapter and existing Control Plane modules.
- Produces: a verified repository state and a precise list of files required by the live MCP runtime.

- [ ] **Step 1: Add/record focused verification evidence**

Run the TaskStore and MCP tests and record exact pass counts in the execution ledger.

- [ ] **Step 2: Verify repository-wide quality**

Run: `.venv/bin/ruff check .`; `.venv/bin/python -m py_compile creator_app/agnes/mcp_server.py creator_app/control_plane/task_store.py`; `.venv/bin/python -m pytest -q`; `git diff --check`.
Expected: Ruff and diff checks pass; compile succeeds; full tests pass with no new failures.

- [ ] **Step 3: Build the targeted deployment set**

Compare the repository MCP adapter/control-plane files with `/opt/cknexus-mcp`. Identify only the adapter and required TaskStore/control-plane dependencies. Do not copy the repository wholesale. Capture SHA-256 hashes of each target live file before changing it.

- [ ] **Step 4: Verify deployment prerequisites**

Confirm `cknexus-agent` owns the live application and state directory, MCP remains loopback-only, current service environment does not expose hosted inference keys, and there is sufficient free disk for the small SQLite state file and backup copies.

- [ ] **Step 5: Run the affected live-independent integration check**

Run the MCP application test suite in the repository environment and a local temporary-database canary that exercises enqueue → claim → checkpoint → finish → status.

- [ ] **Step 6: Commit the passing deliverable**

No automatic Git commit; retain the dirty worktree.

### Task 3: Stage and deploy the MCP task queue safely

**Files:**
- Modify only the exact live MCP files identified in Task 2 under `/opt/cknexus-mcp`
- Create: service-user-owned state directory/file under `/home/cknexus-agent/.local/state/cknexus/` or the service user's resolved home state path
- Create: timestamped deployment backup outside the application tree

**Interfaces:**
- Consumes: verified repository adapter and exact dependency file list from Task 2.
- Produces: live MCP service exposing the five queue tools while preserving existing planning/authentication tools and network boundary.

- [ ] **Step 1: Add the live deployment canary script/test**

Run a pre-change script that records service state, listening address, exact file hashes, and MCP initialize response. Abort if MCP is not active, the bind is no longer loopback-only, or required backup hashes cannot be recorded.

- [ ] **Step 2: Verify the relevant pre-deployment state**

Run: `systemctl is-active cknexus-mcp.service`; socket/listener inspection for port 8765; MCP initialize HTTP canary; SHA-256 over target files.
Expected: service active, port only on `127.0.0.1:8765`, initialize returns valid JSON-RPC HTTP 200, and all target hashes are recorded.

- [ ] **Step 3: Stage exact files and state path**

Back up exact target files. Copy only the reviewed adapter and required control-plane modules. Set ownership to `cknexus-agent` and restrictive file permissions. Do not alter service unit configuration unless the existing unit cannot resolve the documented state path; if a unit change is unavoidable, stop and report before modifying it.

- [ ] **Step 4: Verify the focused live pass**

Run the focused MCP tests using the live virtual environment and a local temporary task database; then restart only `cknexus-mcp.service` and immediately verify active state and port binding.
Expected: focused tests pass; service returns active; no new failed unit appears.

- [ ] **Step 5: Run the affected integration check**

Run MCP initialize, tools/list, and a non-production queue canary using a temporary test task. Confirm the task reaches completed state, status does not expose the lease token, and no model/provider call occurs. Confirm API Gateway, Scanner, Watchdog, and required Docker containers remain healthy.

- [ ] **Step 6: Commit the passing deliverable**

No Git commit. Deployment changes are recorded by file hashes and the execution ledger.

### Task 4: Post-deployment verification and rollback gate

**Files:**
- Modify: `docs/plans/2026-10-22-phase-abc-hardening-report.md`
- Modify: `progress.md`
- Create: deployment evidence under the existing `evidence/` convention

**Interfaces:**
- Consumes: live MCP queue tools and pre-deployment backup/hash records.
- Produces: verified operational evidence or an exact rollback if any gate fails.

- [ ] **Step 1: Add focused post-deploy assertions**

Assert MCP remains loopback-only, initialize and tools/list succeed, all five queue tools are discoverable, a test task can complete, stale lease-token writes are rejected, and status output contains no lease token.

- [ ] **Step 2: Verify the deployment result**

Run: MCP canaries, `./scripts/ck-health`, focused queue tests, and `systemctl --failed --no-pager`.
Expected: queue canaries pass; health remains at least as healthy as pre-deploy except for known pre-existing disk/Git/OpenClaw warnings; no failed service is introduced.

- [ ] **Step 3: Roll back on any deployment regression**

If any deployment-specific canary fails, restore the exact backed-up live files, restore their ownership/permissions, restart only `cknexus-mcp.service`, and repeat initialize, listener, and health checks. Do not attempt an alternative live implementation without returning to the verified baseline first.

- [ ] **Step 4: Verify the final state**

Run: `.venv/bin/pytest -q`, `.venv/bin/ruff check .`, `git diff --check`, live MCP canaries, and `./scripts/ck-health`.
Expected: repository checks pass and the live MCP service is active with the documented queue interface and security boundary.

- [ ] **Step 5: Record evidence**

Update the hardening report with exact test counts, live service state, listener state, deployment file hashes, and any remaining warnings. Never include secrets or lease tokens in evidence.

- [ ] **Step 6: Commit the passing deliverable**

No Git commit unless separately requested by the user.

---

## Unresolved externally observable decisions

- The MCP adapter's stable error-code strings are an implementation detail unless an existing client already depends on a specific error vocabulary; before exposing the tools to an external client, preserve whatever existing MCP error envelope the server already uses rather than inventing a second transport format.
- The exact default state-home path is derived from the live service user's home and may differ from `/home/cknexus-agent`; the deployment task must use the actual `getent passwd cknexus-agent` home value rather than hard-code it.
