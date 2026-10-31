# Automation Catalog and Execution Order

## Priority order

### P0 — Read-only foundation

1. Repository baseline: branch, SHA, dirty state, instructions, open PR, CI policy
2. Work identity: work_id, base_sha, risk, capabilities, idempotency key
3. Connector preflight: discovery, schema hash, risk and authorization
4. Task graph planning: research, implementation, verification, security
5. Local verification: tests, Ruff, secret scan, pip-audit, evidence

Rollback: discard plan/workspace; no remote mutation.

### P1 — Controlled GitHub flow

1. Create allowlisted branch
2. Push verified commit
3. Create Draft PR with evidence link
4. Read checks and review feedback
5. Change to ready only under policy

Rollback: close PR/branch only when work_id ownership and artifact identity match. Never force-push.

### P2 — Staging promotion

1. Verify sandbox profile and cgroup enforcement
2. Verify distributed idempotency
3. Deploy staging with canary/health checks
4. Collect logs/evidence
5. Roll back on failed health or policy gate

Production remains blocked until an explicit separate policy is approved.

### P3 — Event/schedule automation

1. GitHub PR/check event monitoring
2. stale-work reconciliation
3. health report
4. evidence retention cleanup

Every trigger must define owner, resource scope, cadence, data minimization, failure action, retry bound, rollback and disable command. Create live triggers only after review.

## Automation state

`DRAFT -> VALIDATED -> ENABLED -> RUNNING -> SUCCEEDED | BLOCKED | FAILED -> DISABLED`

A failed automation never silently retries a mutation. Retry must be idempotent and bounded.

## Free-first profile

Use repository Git, GitHub connector, local Python/pytest/Ruff, public web research, existing CK-NEXUS modules and read-only checks first. Do not assume paid SaaS, paid model, paid runner or paid connector. If a capability is unavailable, record `BLOCKED_CAPABILITY` and preserve a manual fallback.
