# CK-NEXUS R9–R11 Canonical Implementation Validation

Baseline: R8 `ded79e08b930b5a6b733bcc658bfc9615d1b09a8` (`r8-encrypted-vault`).
Branch: `r9-r11-canonical-implementation`.
Canonical source: `CK-NEXUS-CANONICAL-MASTER-SOURCE-R9-R12.md`, revision 1, sections 5–7.

Release posture: **Development Candidate / Release Candidate / NO-GO**.

## Verified locally

- Canonical R9–R11 targeted tests: **23 PASS**.
- R8 + R9–R11 non-billing regression: **118 PASS**.
- Full pytest: **124 PASS / 3 errors**. All three errors are billing fixtures blocked because `aiosqlite` is unavailable in this environment.
- Python compileall: PASS.
- `git diff --check`: PASS.
- JSON schema / pattern registry / TOML parse: PASS.
- Gateway routing/auth/permission/SSRF boundary unit paths: PASS.
- Shared token-budget behavior through two in-memory limiter instances sharing one state object: PASS as unit proof only.
- R10 six-pattern registry, deterministic selector, state-machine guardrails and execution-controller audit seam: PASS.
- R11 typed graph edges, dedup linking, lens selection, scoring, audit-preserving updates, proposal-only boundary: PASS.

## Correctly BLOCKED / unavailable

- `R9_RATE_LIMIT_CLUSTER`: **BLOCKED**. The local sandbox has no `redis` Python package / real Redis staging service. `scripts/r9_rate_limit_cluster.py` returns machine-readable BLOCKED with exit code 2 and does not fall back to the process-local limiter.
- Full billing fixtures: BLOCKED by missing `aiosqlite`.
- Fresh `uv lock --check --offline`: BLOCKED because the offline cache lacks `asyncpg` for all supported platform/Python splits; this is not evidence that the dependency graph fails online.
- Ruff: binary unavailable.
- Bandit: binary unavailable.
- pip-audit: binary unavailable.

## Security assertions verified by code/tests

- Raw `Authorization`, cookies and proxy authorization headers are stripped before the upstream client seam.
- Default HTTP proxy client does not follow redirects.
- Upstreams are configured service IDs; arbitrary client-supplied hosts are not routed.
- JWT verifier requires issuer, audience, expiry/issued-at, subject and tenant mapping.
- Route permission check occurs before proxy execution.
- Redis limiter key fragments are normalized and policy-versioned.
- Redis failure on fail-closed policy returns a safe 503 rather than silently bypassing the rate limit.
- Pattern forbidden tools override actor role/permission.
- Kill switch, circuit state, approval, timeout, credential scope and idempotency are guardrail inputs.
- Idea Engine cannot deploy, publish, send outbound messages, mutate billing, export credentials, mutate approvals or alter release gates.
- Idea graph preserves prior state in audit history when updating/archiving nodes.

## Not production evidence

The following remain mandatory before any Production Ready claim:

- real Redis with 2+ gateway instances and restart-preserved shared budget evidence;
- PostgreSQL concurrency/dedup gates;
- live OpenAI AI001 through the production runtime path;
- real n8n routing and `n8n audit` evidence;
- backup/restore destructive drill in isolated staging;
- injected-failure alert delivery;
- clean-machine deployment of the exact artifact;
- one exact commit/artifact/environment identity across every required R12 gate.
