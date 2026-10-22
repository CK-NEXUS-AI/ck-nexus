# CK-NEXUS Autonomous Repair Worker Design

**Goal:** Add a bounded worker seam that consumes the existing durable control-plane queue, executes only approved sandbox work, verifies the outcome, and records evidence without authorizing production mutation.

## Scope

This phase is B — Autonomous Repair. It builds on the existing `TaskStore`, `ControlPlaneOrchestrator`, and `ControlPlaneVerifier`. It does not replace the queue, introduce another scheduler, call paid model APIs, or grant production write authority.

## Architecture

`TaskStore` remains the durable source of task ownership and lease fencing. A new worker component will claim one leased task at a time, invoke an explicit worker adapter, checkpoint lifecycle state, run verification through `ControlPlaneVerifier`, and finish the task with a bounded outcome. Repair attempts are bounded and cannot mutate production; the worker returns evidence references and a NO-GO production status.

### Lifecycle

`queued → running/executing → verifying → completed | failed`

A lease expiry returns an unfinished task to the queue subject to the existing retry budget. A verification failure may invoke the repair adapter only within the configured repair budget. An expired lease or exhausted repair budget results in failure, never implicit success.

## Components

### 1. AutonomousRepairWorker

Single-responsibility worker loop over `TaskStore`.

Responsibilities:
- claim a task using an explicit worker ID and bounded lease;
- execute through an injected adapter rather than hard-coding model/provider calls;
- persist checkpoints at execution and verification boundaries;
- call the existing verifier with test/security/evidence results;
- perform bounded repair attempts when verification fails;
- finish using the original lease token, so stale workers are fenced;
- never expose lease tokens in status/evidence output;
- return `production_status=NO-GO` and `release_evidence=false` unless the verifier explicitly establishes verification evidence; even then production mutation remains unauthorized.

### 2. WorkerAdapter interface

The worker receives a task payload and returns a deterministic structured result containing execution state, test result, security result, evidence references, and optional repair callback information. The adapter is dependency-injected so tests can use a local fake and live deployment can remain sandbox-only.

The default adapter must not invoke Model Studio, OpenAI, Qwen, external inference, or production mutation.

### 3. Verification boundary

`ControlPlaneVerifier` remains the only release-evidence gate. Empty or blank evidence references are invalid. Verification infrastructure exceptions are failures/retries, not proof of success. `patch_applied` remains false in this phase.

## Safety boundaries

- Maximum repair attempts: configurable but bounded, default recommendation 2.
- Maximum worker lease: bounded by existing `TaskStore` limit.
- One claimed task per worker iteration; no unbounded fan-out.
- No production credentials are accepted in task payloads.
- No production mutation interface is exposed by the worker.
- No external model/inference call is made by the default adapter.
- Stale lease tokens cannot checkpoint or finish a task.
- Task status must not expose lease tokens.

## Failure semantics

| Condition | Outcome |
|---|---|
| No queued task | Worker returns idle/no-op |
| Adapter raises | Checkpoint failure and finish failed |
| Verification fails, repair budget remains | Run bounded repair and re-verify |
| Verification fails after budget | Finish failed |
| Evidence empty/blank | Verification fails |
| Lease expires | Worker loses authority; requeue mechanism may reclaim |
| Stale worker tries checkpoint/finish | Lease conflict; no state overwrite |
| Production mutation requested | Reject as NO-GO |

## Testing strategy

Use TDD at the public worker boundary. Required focused behaviors:
1. successful execute → verify → finish;
2. execute failure produces failed task and checkpoint;
3. verification failure triggers at most the configured repair count;
4. empty evidence cannot produce release evidence;
5. stale lease cannot finish a reclaimed task;
6. default adapter makes no external model/API call and exposes no production mutation capability.

Integration coverage will exercise the real SQLite `TaskStore` and real `ControlPlaneVerifier` with only the worker adapter mocked/faked at its external boundary.

## Explicit non-goals

- No automatic production deployment.
- No autonomous credential rotation.
- No paid inference.
- No replacement of `TeamDirector` or `ControlPlaneOrchestrator`.
- No unrestricted multi-agent parallel execution in this phase; that is phase C.
