# CK-NEXUS Phase A → B → C Hardening Report

Date: 2026-10-22
Repository: `/root/ck-nexus`
Live MCP runtime: `/opt/cknexus-mcp` (separate non-Git deployment tree)

## Phase A — Reliability baseline

- Disabled `fwupd-refresh.timer` on the QEMU VPS after read-only inventory showed no configured UEFI ESP and no firmware-updatable device; reset the stale failed service state. This stops a recurring metadata refresh failure for a firmware workflow that is not usable in this guest. It can be re-enabled if the host gains supported firmware update capability.
- Removed only regenerable APT package cache indexes (`pkgcache.bin`, `srcpkgcache.bin`); no installed packages, Docker images, volumes, logs, secrets, or application data were removed.
- Added Ruff `extend-exclude = ["evidence/**"]` because the evidence archive contains checksummed historical artifacts and should not be rewritten by formatters. The archived files were left untouched.
- Reformatted and fixed lint findings in active source/runbook/test files. Repository-wide `ruff check .` now passes.
- Fresh live health check: systemd is `running`, no failed units; MCP, API Gateway, Scanner, and Watchdog timer are active; MCP remains bound to `127.0.0.1:8765`; MCP initialize returns HTTP 200.
- Remaining operational warning: root filesystem is about 90% used (~3.9 GiB free), above the health threshold of 85%. Storage accounting shows the largest consumers are in-use Docker/containerd images and volumes, installed tools, and a 2.3 GiB separate sandboxd containerd store. These were not pruned because their ownership/use could not be safely ruled out. Memory is 1.9 GiB total with substantial swap in use; no service was killed or restarted for memory reclamation.

## Phase B — Queue and recovery safety

File: `creator_app/control_plane/task_store.py`

- Expired running jobs are requeued only within a bounded attempt budget (default 3, configurable 1–10); exhausted jobs become `failed` rather than cycling indefinitely.
- Claim lease duration rejects negative, non-finite, and over-24-hour values.
- Each claim receives a cryptographically random lease token. Checkpoint and finish operations require a currently valid lease plus matching worker ID and token, preventing stale workers from writing after a job is reclaimed, even when the worker ID is reused.
- Lease tokens are cleared on requeue/terminal state and omitted from status responses.
- SQLite schema migrates older task tables by adding the lease-token column. The database file is restricted to mode 0600.
- Persistence, duplicate-ID, atomic-claim, retry-exhaustion, stale-worker, lease-boundary, schema-migration, and token-redaction tests are covered.

## Phase C — Multi-agent and verification correctness

Files: `creator_app/control_plane/orchestrator.py`, `creator_app/control_plane/verification.py`

- The orchestrator returns `COMPLETED` only when a non-empty graph has a completed result for every node. Empty graphs and dependency cycles fail closed instead of being misreported as successful.
- Verification requires non-empty, non-blank evidence references.
- Verification callback exceptions are bounded by the retry budget and never count as success.
- These components do not apply or commit patches themselves; sandbox and security gates remain separate.

## Verification evidence

- Final full suite, after the final code edits: `767 passed, 2 skipped, 1 warning in 48.90s`.
- Repository-wide Ruff: passed.
- Python compile check for modified control-plane modules and tests: passed.
- `git diff --check`: passed.
- Focused TaskStore suite: `14 passed`.
- Fresh live health check: `WARN` only for disk pressure, Git divergence/dirty worktree, and OpenClaw CLI absent from the VPS PATH. No failed systemd units were reported.
- The one test warning is a Starlette deprecation for `HTTP_422_UNPROCESSABLE_ENTITY`; it is not a failing test.

## Deployment boundary

The live MCP service runs as `cknexus-agent` with `WorkingDirectory=/opt/cknexus-mcp`; `/opt/cknexus-mcp` is not a Git checkout and is separate from `/root/ck-nexus`. The repository changes have **not** been copied into that live tree or deployed/restarted. The live `mcp_server.py` currently exposes planning tools; the new queue store is not yet wired to MCP tools. Runtime integration is a separate staged change with backup, service-user-owned state storage, contract tests, restart/rollback procedure, and a post-deploy MCP canary.

## Next step

Design document created at `docs/specs/2026-10-22-mcp-task-queue-integration-design.md`. It defines a narrow MCP task-queue interface with durable state, lease ownership, checkpointing, no model/API calls, no direct shell execution, and no automatic production mutation. It requires operator review before implementation/deployment. No commit, merge, rebase, or push was performed.
