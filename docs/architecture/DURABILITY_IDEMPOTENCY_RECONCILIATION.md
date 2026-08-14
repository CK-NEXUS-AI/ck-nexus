# Durability, Idempotency, and Reconciliation

Status: architecture contract.

## Core rule

Every impactful execution follows `Prepare -> Authorize -> Execute -> Observe -> Reconcile -> Verify -> Commit Evidence`. A network acknowledgement is not equivalent to a verified business outcome.

## Durable action journal

Before an external mutation, CK-NEXUS durably records an action intent containing operation ID, task ID, tenant, capability, target fingerprint, semantic idempotency key, request hash, policy/approval references, expected side effect, and preconditions.

Journal states:

`PREPARED`, `AUTHORIZED`, `DISPATCHED`, `OBSERVED`, `COMMITTED`, `COMPENSATING`, `COMPENSATED`, `FAILED`, `UNKNOWN`.

State transitions are append-only events; a materialized current state may be rebuilt.

## Idempotency keys

Keys are semantic, not merely random request IDs. Key material should bind tenant + capability + stable target + business operation + relevant version/window. Sensitive values are hashed/redacted.

Connector capability manifests declare idempotency behavior:

- native provider idempotency;
- CK dedupe-only;
- conditional;
- not idempotent.

## Reconciliation

Reconciliation answers: did the external business effect happen, exactly once, with the expected result?

It uses provider-native lookup IDs, read-after-write verification, event/webhook correlation, state comparison, and time-bounded polling. When no reliable read path exists, commit confidence remains limited and is surfaced explicitly.

## Once-only consumption

Workflow events use consumer idempotency records and monotonic attempt counters. Event replay is allowed, duplicate side effects are not.

## Recovery

After process restart, AGNES scans nonterminal journal entries and routes them to reconciliation before any retry. Stale leases may be reclaimed only under lease/token fencing rules.

## Data stores

Production-impact paths require durable storage suitable for distributed coordination. In-memory state is development-only. If required durable dependencies are unavailable, fail closed.

## Evidence

Execution receipts bind request hash, response observation, provider request IDs when safe, idempotency key hash, before/after fingerprints, reconciliation method, commit confidence, verifier result, and journal event range.
