# Durable Execution Reconciliation V3

Status: DEVELOPMENT / MEASURED_NOT_VERIFIED ceiling

## Authority boundary

This reconciliation imports the useful durable-execution semantics from
`post-p0/durable-execution-correctness-v2` without importing a second
verification authority or any external executor.

Included:
- deterministic checkpoints
- replay and restore
- bounded fork semantics
- origin-bound lineage verification
- idempotent durable signals
- explicit-clock timers
- reverse-order compensation planning
- local atomic checkpoint persistence with fsync

Excluded on purpose:
- `ExecutionReceipt` self-classification into VERIFIED
- provider/network execution
- production mutation
- credential handling
- self-approval

## Hardening over the source branch

1. A run cannot fork from a checkpoint belonging to another run.
2. A fork must use a distinct run ID.
3. First checkpoint lineage can be bound to an expected origin digest.
4. Cross-run lineage and decreasing step order fail closed.
5. Parent/origin digests use strict lowercase SHA-256 validation.
6. Local checkpoint writes flush file content before atomic replacement and
   fsync the directory when supported.
7. Completion refuses unresolved pending writes.

## Verification requirement

GitHub CI and focused regression are measurement only. Independent verifier
acceptance of the exact subject is still required before any VERIFIED claim.
This branch does not alter Q10/Q11/Q12 or production certification state.
