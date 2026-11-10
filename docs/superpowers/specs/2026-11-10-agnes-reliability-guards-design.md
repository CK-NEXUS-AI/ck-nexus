# Agnes Reliability Guards — Design

**Date:** 2026-11-10
**Status:** Approved by explicit user opt-out of clarification/approval pauses; implementation remains local-only.
**Baseline:** `56635362db8dde2c9e8b67a4b59bc6a9423b439c`
**Branch:** `feat/agnes-persistent-ops-memory-20261110`

## Intent

Close the three known reliability gaps in Agnes bounded parallel execution: duplicate queue submissions, cooperative cancellation of active work, and a shared concurrency ceiling across simultaneous TeamDirector requests.

## Existing facts

- `TaskStore` uses SQLite and `job_id` as a primary key, so duplicate job IDs are rejected; it has no caller-supplied idempotency key.
- `AgentMessageBus` has an in-memory idempotency cache scoped to `(sender, recipient, key)`; it does not cover durable queue submissions or survive process restart.
- `ParallelExecutor` creates an executor per request and uses `run_in_executor` for synchronous workers. `asyncio.wait_for` cannot terminate a running Python thread.
- `TeamDirector` creates a `ParallelExecutor` per request. The per-request semaphore does not cap concurrent requests or multiple TeamDirector instances.
- Built-in Agent `process` methods are synchronous and currently do not expose a cancellation contract.

## Approaches

1. Add a new task broker / agent framework: rejected because it duplicates existing SQLite queue and executor abstractions.
2. Add durable idempotency to TaskStore, cooperative cancellation to the existing Agent contract, and a process-wide shared semaphore: selected as the smallest compatible change.
3. Use process isolation to forcibly terminate arbitrary synchronous agents: deferred because Agent/provider objects and current contracts are not designed for safe process serialization; introducing it would be a separate architecture migration.

## Decisions

- `TaskStore.enqueue` and `enqueue_many` accept optional idempotency keys. A repeated key with identical canonical payload returns/reuses the original job identity; the same key with a different payload is rejected. Existing `job_id` duplicate behavior remains intact. SQLite uniqueness and an immediate transaction enforce concurrent callers.
- MCP enqueue adapters accept optional idempotency keys and pass them to TaskStore. The four-role batch derives one child key per node from the caller's batch key.
- Cancellation is cooperative. A request has a stable caller-selectable `request_id`, an event registered while active, and `cancel_request(request_id)`. Built-in agents check cancellation at entry and between work phases. A cooperative worker acknowledges cancellation; arbitrary third-party synchronous Agent code that never checks the event cannot be forcibly stopped by Python threads and must remain reported as non-cooperative.
- `TaskStatus.CANCELLED` is explicit. Cancellation must never be reported as COMPLETED. Pending descendants are marked CANCELLED/BLOCKED consistently; completed work remains recorded as completed.
- A module-level bounded semaphore caps TeamDirector worker execution across all TeamDirector instances and requests in one Python process. The default process-wide ceiling is 2 to preserve Termux/mobile headroom. This does not claim cross-process coordination; that requires a shared durable lease/worker architecture and remains an explicit limitation.
- The existing per-request limit remains in force; effective execution is bounded by both limits.
- No Core/L3 authority, credentials, external tools, release gates, VPS, deployment, or production behavior changes.

## Acceptance criteria

- Durable duplicate enqueue with the same idempotency key and payload returns the same effective job ID without adding a row.
- Reusing an idempotency key with a different payload fails closed; concurrent duplicate submissions create exactly one row.
- MCP single and batch enqueue accept bounded idempotency keys without weakening existing validation or execution gates.
- A caller can cancel a running TeamDirector request by known request ID; cooperative workers stop at cancellation checkpoints and results show CANCELLED, never COMPLETED.
- A cancelled request does not start later dependency waves; completed prior steps remain completed.
- Concurrent requests across separate TeamDirector instances never exceed the process-wide worker ceiling.
- Existing synchronous and async APIs remain compatible.
- Full focused regression, Ruff, compileall, and diff checks pass.

## Non-goals / limitations

- Hard-killing arbitrary Python threads is impossible. A non-cooperative synchronous Agent may continue until its current call returns; cancellation is signalled but not forcibly terminated.
- The process-wide semaphore does not coordinate separate OS processes or hosts.
- This change does not create production authority or prove Production readiness.
