# CK-NEXUS MCP Task Queue Integration — Design

Date: 2026-10-22
Status: Proposed; awaiting operator review before implementation/deployment.

## 1. Goal

Expose the existing durable `TaskStore` through the current loopback-only CK-NEXUS MCP service so a connected assistant can persist, claim, checkpoint, resume, and finish bounded development tasks. This is a task-lifecycle API, not a shell executor or production deployment mechanism.

## 2. Current system facts

- Repository under development: `/root/ck-nexus`.
- Live MCP service: `cknexus-mcp.service`, running as `cknexus-agent` from `/opt/cknexus-mcp`.
- Live MCP is loopback-bound at `127.0.0.1:8765`; a post-deployment canary must preserve that boundary.
- `creator_app/control_plane/task_store.py` now provides a SQLite queue, bounded expired-lease retries, per-claim random lease tokens, stale-worker fencing, additive schema migration, database mode 0600, and a status response that does not expose the lease token.
- The live tree is not a Git checkout. It must not be overwritten wholesale from the repository.

## 3. Recommended architecture

Add a thin MCP adapter in `creator_app/agnes/mcp_server.py` that calls `TaskStore`; keep persistence and lease rules in `creator_app/control_plane/task_store.py`. Do not add another agent framework, database server, provider, or model dependency.

State database path:
- Use `CKNEXUS_TASK_DB` when explicitly configured.
- Otherwise use `~/.local/state/cknexus/control-plane.sqlite3` for the service account.
- The state directory must be service-user-owned; SQLite database mode is 0600. No credentials or provider API keys belong in the task database.

## 4. Proposed MCP tools

1. `cknexus_task_enqueue(job_id, description, priority=2, context="")`
   - Validates bounded text and priority; stores a queued task.
   - Duplicate IDs return a stable conflict error.
   - Does not execute code or call an LLM.

2. `cknexus_task_claim(worker_id, lease_seconds=300)`
   - Claims one queued task atomically.
   - Returns task payload, attempt count, expiry, and the random lease token to that claimant only.
   - Lease duration is bounded; default retry budget is three attempts.
   - Empty queue returns an explicit no-work result.

3. `cknexus_task_checkpoint(job_id, worker_id, lease_token, checkpoint)`
   - Saves a size-limited JSON checkpoint only while the lease is valid and both worker ID and token match.
   - Stale or expired workers receive a lease-conflict result.

4. `cknexus_task_finish(job_id, worker_id, lease_token, success, result=None, error=None)`
   - Finishes only for the current valid lease owner.
   - Clears the lease token when the task is terminal.
   - Task completion is workflow state only; it must always report `release_evidence=false` and `production_status=NO-GO`. It cannot certify a release.

5. `cknexus_task_status(job_id)`
   - Returns task state, attempts, timestamps, checkpoint/result metadata, and sanitized error information.
   - Never returns the lease token.

## 5. Security and failure behavior

- No tool runs shell commands, applies patches, commits, deploys, restarts services, calls hosted models, or forwards credentials.
- Keep the existing MCP loopback-only bind and authenticated remote boundary unchanged.
- Bound request/checkpoint/result sizes and validate identifiers, priorities, worker IDs, and lease durations.
- Reject obvious secret-shaped values and sensitive field names in persisted payloads as defense in depth; do not claim pattern matching can detect every possible secret. Callers must not submit credentials or private keys.
- Do not include lease tokens in logs, status output, checkpoint data, or evidence artifacts.
- Expired leases requeue only within the configured retry budget; exhausted jobs become `failed`.
- Verification or worker failure is never converted to release evidence. Existing sandbox, security review, and verification gates remain the only route to verified development evidence.
- Tool errors use stable error codes for invalid input, duplicate job, missing job, empty queue, and lease conflict; no raw stack traces or secret-bearing payloads are returned.

## 6. Tests and deployment gate

Add MCP adapter contract tests in `tests/test_control_plane_mcp.py` (or a focused new queue test module) using a temporary `CKNEXUS_TASK_DB` and fake task handlers. Tests must cover:
- enqueue/claim/checkpoint/finish/status happy path;
- empty queue and duplicate job behavior;
- expiry, retry exhaustion, and stale lease-token rejection;
- status output never contains the token;
- database file permissions and migration from the pre-token schema;
- size/secret-shaped payload rejection;
- no LLM or external network calls.

Deployment steps after review:
1. Run the full repository tests, Ruff, and diff checks.
2. Back up the specific live MCP files and record SHA-256 hashes.
3. Stage only the reviewed adapter and required control-plane modules into `/opt/cknexus-mcp`; do not copy the entire repository.
4. Verify file ownership and permissions as `cknexus-agent`, run focused tests in the live virtual environment, then restart only `cknexus-mcp.service`.
5. Confirm service active, MCP initialize and tools/list canaries pass, port remains `127.0.0.1:8765`, API Gateway health remains unchanged, and no model/provider API call occurred.
6. On any failed canary, restore the exact backed-up files and restart the service, then verify recovery.

## 7. Explicit non-goals

- No background worker loop in this change.
- No automatic source-code patching or production mutation.
- No claim that a task is verified merely because its queue state is completed.
- No deletion of sandbox/container data to address disk pressure.
- No Git commit, merge, rebase, or push.

## 8. Review decision

Recommended: approve this narrow queue API and its deployment gate as written. If approved, create the implementation plan and proceed through tests, staged deployment, and post-deployment canary verification.
