# CK-NEXUS — n8n Development Intelligence Auto Design

**Date:** 2026-10-24
**Status:** Approved for implementation by the user's explicit "เริ่มเลย" instruction
**Goal:** Turn n8n execution/workflow telemetry into a safe, durable CK-NEXUS development signal that can automatically create prioritized development work without allowing n8n or an AI model to execute arbitrary shell/Git commands.

## 1. Current state

CK-NEXUS already has a bounded Control Plane with a durable SQLite `TaskStore`, verification gate, worker lease/checkpoint model, and a Hybrid Fast Control Plane. The existing n8n Workflows UI reads `workflows` and `executions` through a restricted read-only adapter. The VPS is resource constrained, so the new collector must use bounded polling and concurrency 1.

The current repository also contains unrelated/pre-existing modifications. The implementation MUST preserve them and MUST NOT use blanket staging such as `git add -A`.

## 2. Target architecture

```text
n8n API (read-only)
       |
       v
N8N Telemetry Collector
       |
       v
Normalizer / Event Contract
       |
       +--> SQLite event ledger (dedupe + checkpoint)
       |
       v
Classifier
  | success / info / warning / failure
  | bug / performance / reliability / workflow / security
       |
       v
Development Intelligence
       |
       +--> deterministic priority + risk
       |
       v
TaskStore
       |
       v
Existing Control Plane Worker
       |
       v
Verification / Evidence
       |
       v
Future Auto-GitOps gate
```

n8n is a **telemetry source**, not the authority for code mutation. AI may enrich or summarize a signal later, but the first implementation is deterministic and does not depend on an AI provider.

## 3. Event contract

Every accepted n8n execution becomes a normalized event with:

- `event_id`: stable SHA-256 fingerprint of source + execution + relevant failure identity.
- `source`: `n8n`.
- `workflow_id`, `workflow_name` when available.
- `execution_id`.
- `status`: normalized execution status.
- `severity`: `info`, `warning`, `high`, or `critical`.
- `category`: `success`, `failure`, `performance`, `reliability`, `workflow`.
- `message`: sanitized diagnostic summary; credentials, tokens, and large payloads are never stored.
- `observed_at`.
- `metadata`: bounded non-secret metadata only.

## 4. Development signal rules

Only actionable events create development tasks.

- Failed execution -> `bug` or `reliability` task depending on failure pattern.
- Repeated failure for the same fingerprint -> increase priority, never create an unbounded duplicate queue.
- Slow execution above configured threshold -> `performance` task.
- Successful execution -> telemetry only; it must not create development work.
- Unknown/malformed n8n payload -> telemetry error only; do not create a code task.

Default thresholds:

- `N8N_INTEL_POLL_SECONDS=120`
- `N8N_INTEL_SLOW_SECONDS=30`
- `N8N_INTEL_REPEAT_THRESHOLD=3`
- `N8N_INTEL_MAX_EXECUTIONS=50`
- collector concurrency: `1`

## 5. Safety model

The collector is strictly read-only against n8n.

It MUST:

1. Read the API key from `/root/.config/n8n/api_key` or an explicitly configured root-owned file; never log it.
2. Allow only `GET` requests to the executions endpoint used by the collector.
3. Bound response size and number of executions processed per cycle.
4. Sanitize error text before persistence.
5. Deduplicate by stable event fingerprint.
6. Use SQLite with WAL and file mode `0600` for the local ledger.
7. Enqueue only typed Control Plane payloads; no shell command field is accepted.
8. Never call `git`, `docker`, `systemctl`, or arbitrary subprocesses from the collector.
9. Fail closed on authentication, schema, or transport errors.

## 6. Task contract

Generated tasks use the existing `TaskStore` and a fixed handler role:

- handler: `n8n_development_signal`
- node/task fields contain a sanitized description and evidence reference.
- `production_status=NO-GO`
- `external_mutation_authorized=false`
- release authority remains with the existing verification/policy layers.

The collector must be idempotent: the same n8n execution/failure fingerprint can be observed repeatedly without creating duplicate tasks.

## 7. Persistence

A local SQLite database stores:

- collector checkpoint / last observed execution marker
- normalized events
- event fingerprint uniqueness
- task linkage
- repeat count
- first/last observed timestamps

The database lives outside the repository's tracked source tree, under `/var/lib/cknexus/n8n-intelligence/`, with restrictive permissions.

## 8. Automation

A systemd timer runs the collector every two minutes. A single short-lived process is preferred over a resident daemon because it is cheaper on the VPS and naturally prevents overlapping runs with a lock.

If the collector fails, systemd records the failure and the next cycle retries. Existing n8n data and CK-NEXUS source files are never modified by a failed collection cycle.

## 9. Integration boundary

Phase 1 integrates only:

`n8n -> intelligence ledger -> TaskStore`

Phase 2 can connect the generated tasks to the existing Control Plane worker and evidence system.

Phase 3 can connect verified development outcomes to the Auto-GitOps system. Auto push must remain behind the separate Git safety gate and must never be triggered directly by n8n telemetry.

## 10. Observability

Each cycle emits a compact audit record containing:

- cycle timestamp
- number fetched
- number accepted
- number ignored
- number new events
- number duplicate events
- number tasks created
- last checkpoint
- outcome/error class

No API keys, authorization headers, full execution data, or secret-bearing payloads may appear in logs.

## 11. Non-goals

- No arbitrary n8n workflow mutation.
- No automatic execution of shell commands generated by AI.
- No direct `git commit` or `git push` from this collector.
- No storage of full n8n execution payloads.
- No high-concurrency polling.

## 12. Success criteria

The feature is considered operational only when:

1. Unit tests cover normalization, sanitization, fingerprinting, classification, dedupe, priority, and task payload safety.
2. An integration test proves a failed execution creates exactly one task and repeated polling does not duplicate it.
3. An authentication/schema failure produces no task.
4. `git diff --check` passes.
5. Targeted Ruff/tests pass.
6. The systemd timer is active and a real collector run produces an auditable result.
7. Existing CK-NEXUS tests remain green for the touched area.
