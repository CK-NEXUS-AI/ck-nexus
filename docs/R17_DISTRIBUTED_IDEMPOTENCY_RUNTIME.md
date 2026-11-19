# R17 — Distributed Idempotency Runtime

R17 wires AGNES Phase 3 staging/production execution to a distributed Redis idempotency backend.
Development remains on durable single-host SQLite for deterministic local tests.

## Fail-closed rules

- Phase 3 + `staging`/`production` requires `CKNEXUS_AGNES_REDIS_URL`.
- Only `redis://` and `rediss://` schemes are accepted.
- Missing Redis client fails initialization instead of silently falling back to SQLite.
- Credential-bearing Redis URLs are never included in status/error output.
- No automatic merge or production deployment is introduced.

## PostgreSQL

`migrations/postgresql/003_agnes_idempotency.sql` defines the canonical PostgreSQL table used by the existing `PostgresIdempotencyStore`. Live PostgreSQL and Redis proof remains a runtime gate and must be executed only against an explicitly provisioned non-production/staging target.

## Evidence harness

`scripts/gate_distributed_idempotency.py --require-live` performs duplicate-claim and replay checks against both configured live backends without printing connection URLs. It returns exit 2 when infrastructure or required clients are unavailable.

## Verification in current isolated host

- Targeted R17 + Phase 3 tests: 13/13 PASS.
- Non-billing regression: 175/175 PASS.
- Test collection: 184 tests.
- Billing: 6 PASS / 3 ERROR because `aiosqlite` is unavailable in the host environment.
- Python compile: PASS.
- Secret scan: PASS.
- Active runtime n8n scan: PASS, zero matches.
- Live Redis/PostgreSQL distributed-idempotency gate: BLOCKED because no live URLs/services are configured.
- Ruff/Bandit/pip-audit: BLOCKED because the packages are unavailable and the package registry cannot supply them.

Production verdict remains NO-GO. No production mutation, external message, paid OpenAI request, auto-merge, or automatic deployment was performed.
