# P0 task completion: Core/L3 grant contract

## Authority boundary

A service identity token authenticates a caller; it does not authorize a task to become completed. Successful completion requires a signed, one-time `control_plane.task.complete` grant issued by `CapabilityAuthority` for the exact task and exact persisted result. The grant is bound to `{job_id, result}`; `result` includes the evidence reference.

## Required policy

The example policy registers `control_plane.task.complete` as `adminOnly`, task-scoped, and requiring verified task-bound evidence. Only `OWNER` is granted this capability. Production policy must preserve these restrictions; do not broaden it to ordinary workers or external tools.

## Shared SQLite transaction

`TaskStore` consumes the grant row, validates the signature, capability ID, task ID, expiry, params hash, and verified/unrevoked evidence row, then changes the task state in one `BEGIN IMMEDIATE` transaction. The grant and evidence tables must be in the same SQLite file as `control_plane_tasks`. A separate Authority DB is intentionally rejected by absence of the grant/evidence rows; do not use a cross-database attach as a substitute for atomicity.

Configure `CKNEXUS_TASK_DB` and `CKNEXUS_COUNCIL_AUTHORITY_DB` to the same canonical database path. If `CKNEXUS_TASK_DB` is omitted, the MCP task store uses `CKNEXUS_COUNCIL_AUTHORITY_DB` when present. Configure `CKNEXUS_CAPABILITY_GRANT_SECRET` with at least 32 bytes, and pass the same secret to the trusted `CapabilityAuthority` instance as `grant_secret`. Never place the secret in source control, task payloads, logs, or evidence files. Missing or mismatched configuration fails closed.

## Completion flow

1. Worker executes and verifies work, then stores the exact result/evidence reference.
2. Without a completion grant, the task moves to `awaiting_approval`; its lease is released and it remains visible as open work.
3. Owner/Core L3 verifies and seeds the evidence row for the exact `job_id`, then issues `control_plane.task.complete` with params `{job_id, result}` and context `{taskId: job_id, evidenceRefs: [...]}`.
4. `cknexus_task_approve` consumes the signed grant against the persisted pending result. The grant is one-time; a mismatch, expired grant, replay, unverified evidence, wrong task, or wrong result is denied without completing the task.
5. Task completion is not release certification. `production_status` remains `NO-GO` and `release_evidence` remains false unless a separate release gate proves otherwise.

## Operational note

The configured Core/L3 authority service must use the same database and grant secret as the task store. Do not mark this path production-verified until an integration test exercises the actual deployed authority service, MCP endpoint, and shared database configuration.
