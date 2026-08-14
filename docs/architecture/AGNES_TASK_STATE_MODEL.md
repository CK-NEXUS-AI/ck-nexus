# AGNES Task State Model

Status: architecture contract.

## Task lifecycle

`CREATED -> PLANNING -> READY -> RUNNING -> VERIFYING -> SUCCEEDED`

Alternative terminal/blocked states: `FAILED`, `CANCELLED`, `BLOCKED_POLICY`, `BLOCKED_APPROVAL`, `BLOCKED_DEPENDENCY`, `SECURITY_VETO`, `UNKNOWN`.

Tasks may enter `PAUSED` from eligible nonterminal states and resume only after state/version validation.

## Node lifecycle

Each DAG node tracks semantic capability, selected implementation decision ID, policy/grant refs, attempts, current lease, idempotency key hash, dispatch state, execution receipt, verification state and evidence refs.

## Attempt model

An attempt is immutable. Retry creates a new attempt linked to the previous failure/reconciliation. Fallback to another implementation is also a new attempt and records the capability-decision update.

## Cancellation

Cancellation is cooperative for in-flight external calls. State becomes `CANCEL_REQUESTED` until the executor confirms cancellation or reconciles the external outcome. UI must not claim cancellation prevented a side effect unless verified.

## Pause

Pause prevents new node dispatch. Running nodes follow capability-specific safe pause/cancel policy. Long-lived workflows checkpoint durable state.

## Verification

A node is not `SUCCEEDED` solely because a provider returned 2xx. Required output contract, external side-effect reconciliation and verifier/evidence conditions must pass.

## Task result

Task completion includes final result, completed/failed/skipped nodes, unresolved uncertainty, cost/usage observation, policy/approval trail, and evidence bundle refs.
