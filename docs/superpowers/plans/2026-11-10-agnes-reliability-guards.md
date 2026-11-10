# Agnes Reliability Guards — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-11-10-agnes-reliability-guards-design.md`
**Base:** `56635362db8dde2c9e8b67a4b59bc6a9423b439c`

## Global constraints

- Work only in `~/cknexus-agnes-memory` on `feat/agnes-persistent-ops-memory-20261110`.
- Preserve all pre-existing untracked docs and plan/spec files.
- No VPS, push, merge, deploy, production writes, credential access, or authority expansion.
- Default process-wide TeamDirector worker cap is 2; per-request cap remains 1–5.
- Cancellation is cooperative; do not claim Python can forcibly terminate a running thread.
- All behavior changes use TDD RED → GREEN.

## Task 1 — Durable TaskStore idempotency

**Files:** `creator_app/control_plane/task_store.py`, `creator_app/agnes/mcp_server.py`, `tests/test_control_plane_task_store.py`, focused MCP tests.

1. Add failing tests for duplicate idempotency key + identical payload, conflicting payload, migration from legacy DB, atomic batch replay, and concurrent duplicate enqueue.
2. Run focused tests and confirm expected failures.
3. Add nullable `idempotency_key`, partial unique index, safe schema migration, canonical-payload replay check under `BEGIN IMMEDIATE`.
4. Extend `enqueue` and `enqueue_many` with optional keys while preserving existing call compatibility and duplicate job ID behavior.
5. Extend MCP single enqueue with optional key and batch enqueue with optional batch key (derive child keys per node).
6. Verify focused queue/MCP tests and commit.

## Task 2 — Cooperative cancellation contract

**Files:** new `creator_app/ai_team/cancellation.py`, `agent.py`, `agent_models.py`, `team_director.py`, built-in `agents/*.py`, tests.

1. Add failing tests for cancellation before worker start, during a cooperative worker, cancellation between dependency waves, and cancelled TeamResult status.
2. Confirm RED.
3. Add `CancellationRequested`, context event checks, explicit `TaskStatus.CANCELLED`, stable optional `request_id`, active request registry, and `cancel_request`.
4. Propagate the event to workers and built-in Agent checkpoints; translate cancellation to explicit CANCELLED TaskResults and do not start later waves.
5. Verify focused TeamDirector and ParallelExecutor tests; commit.

## Task 3 — Process-wide concurrency budget

**Files:** `creator_app/ai_team/team_director.py`, `creator_app/ai_team/tests/test_team.py`.

1. Add a failing multi-request/multi-TeamDirector test with a shared concurrency probe.
2. Confirm RED (the existing per-request cap allows aggregate concurrency above the global ceiling).
3. Add a module-level bounded semaphore with a default limit of 2; acquire cancellation-aware and release in `finally` around every synchronous agent invocation.
4. Verify aggregate concurrency never exceeds 2 while each request preserves dependency ordering and its own cap; commit.

## Task 4 — Regression and evidence checkpoint

1. Run focused regression: TeamDirector, ParallelExecutor, TaskStore, control-plane integration, MCP queue, and worker tests.
2. Run Ruff, compileall, and `git diff --check`.
3. Update operations checkpoint with exact test counts, branch SHA, backup SHA, cancellation limitations, and process-vs-cross-process concurrency boundary.
4. Commit checkpoint. Do not push.
5. Perform a separate self-review because no independent subagent execution tool is available; record all findings and residual limitations.

## Review focus

- Concurrent idempotency-key races and payload mismatch.
- Existing TaskStore schema migration and old callers.
- Cancellation races before, during, and between worker steps.
- No false COMPLETED result after cancellation.
- Semaphore release on every exception/cancellation path.
- Shared Agent locks compose correctly with global concurrency.
- No hidden cross-process guarantee or production authority expansion.
