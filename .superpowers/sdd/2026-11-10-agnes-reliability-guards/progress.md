# SDD ledger — plan: docs/superpowers/plans/2026-11-10-agnes-reliability-guards.md

Pre-flight: Task 1 changes TaskStore/MCP queue contracts; Task 2 changes Agent/TeamDirector cancellation semantics; Task 3 consumes the TeamDirector worker invocation boundary; Task 4 verifies all three. No shared files between Task 1 and Task 2 except Task 4 docs.

Backup: `$HOME/.cache/cknexus-agnes-reliability-prechange-20261110.tar.gz`
SHA256: `35fc4ee66bc4abc3e54beff264e34622703dded333b64fa7f716bcb8dcee8605`

Advisor consultation: unavailable on this non-Codex surface; architecture decisions are documented in the spec and remain subject to self-review.

## Execution checkpoint — 2026-11-10

### Task 1 — Durable idempotency

- Implemented nullable `idempotency_key` schema migration and partial unique index in existing SQLite TaskStore.
- `enqueue` and atomic `enqueue_many` accept optional keys, persist only SHA-256 digests (not caller-supplied raw keys), compare canonical payloads excluding transport `job_id`, replay original job IDs for identical content, reject key/payload conflicts, and serialize races with `BEGIN IMMEDIATE`.
- MCP single enqueue and deterministic four-role batch enqueue accept optional caller idempotency keys. Batch derives child keys by node ID and returns original job IDs on replay.
- TDD evidence: initial TaskStore tests RED (3 failures); final TaskStore suite GREEN (21 passed). Concurrent eight-caller duplicate submission creates one effective row; legacy schema migration and batch rollback tested.
- MCP adapter tests were authored but could not be collected in this Termux Python environment because the declared `mcp>=1.13,<2` project dependency is not installed (`ModuleNotFoundError: mcp`). They are not claimed as passing.

### Task 2 — Cooperative cancellation

- Added shared `CancellationRequested` primitive, optional stable `request_id`, active-request registry, `TeamDirector.cancel_request`, event propagation, and explicit CANCELLED outcomes.
- Built-in Analyst, Connector, Designer, Engineer, Guardian and Researcher check cancellation at entry and between work phases. `ParallelExecutor` maps the explicit cancellation exception to CANCELLED.
- Pending steps are marked CANCELLED and later dependency waves do not start; completed prior steps remain completed. Caller task cancellation signals the event before propagating `CancelledError`.
- TDD evidence: three cancellation tests RED before implementation; cancellation tests GREEN after implementation. Cooperative cancellation test confirms the active worker exits and dependent step never starts.
- Limitation: Python cannot forcibly terminate an already-running non-cooperative synchronous worker thread. Third-party Agents must check the supplied `cancellation_event` / `Agent.raise_if_cancelled` at safe checkpoints. A thread blocked in a non-interruptible call can continue until it returns or its timeout expires; no hard-stop guarantee is made.

### Task 3 — Process-wide concurrency

- Added a shared `threading.BoundedSemaphore` with a process-wide cap of 2 across all TeamDirector instances and concurrent requests. Acquisition is cancellation-aware and release is protected by `finally`.
- Existing per-request concurrency setting remains; effective limit is the lower of per-request and process-wide ceilings.
- Test confirms two separate TeamDirector instances cannot exceed the process-wide worker ceiling.
- Limitation: this is per Python process only. It does not coordinate multiple processes, containers, or hosts; cross-process global scheduling requires a durable shared lease/worker service.

### Task 4 — Verification

- Focused regression: **151 passed, 1 warning** (`creator_app/ai_team/tests` plus `tests/test_control_plane_task_store.py`).
- Ruff: PASS across changed AI team, TaskStore, MCP adapter, and tests.
- compileall: PASS for `creator_app/ai_team`, `creator_app/control_plane`, `creator_app/agnes`.
- `git diff --check`: PASS.
- One earlier full focused run had an Android platform expectation mismatch; the test now accepts `android`, which is an explicitly supported platform in `CrossPlatform`.
- MCP adapter integration tests remain UNVERIFIED in this environment due to missing installed `mcp` dependency; project declares it. Do not infer MCP end-to-end verification from TaskStore tests.

### Current disposition

- Idempotency: IMPLEMENTED / TaskStore verified; MCP adapter implementation present, adapter tests blocked by missing dependency.
- Cooperative cancellation: IMPLEMENTED for built-in agents and verified with cooperative test workers; non-cooperative thread termination remains impossible.
- Global concurrency: IMPLEMENTED and verified within one process; no cross-process guarantee.
- WQ-005 remains PARTIAL pending MCP adapter test execution in a correctly provisioned environment, independent review, and any further lifecycle contract decisions.
- No push, merge, deploy, VPS access, production operation, or external authority change occurred.
