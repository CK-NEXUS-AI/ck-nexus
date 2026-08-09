# CK-NEXUS R21 Lock Consistency Gate

Baseline: R20 Observability & Alert Evidence, commit `1e59de013934f249b8d3b1e38fae21fd2eb600dc`, tag `v0.2.0-r20-observability-alerts-dev.1`.

## Increment

R21 adds a required fail-closed `uv.lock` consistency gate. The gate compares every direct project dependency plus the gateway, dev, billing, email, and github-app extras from `pyproject.toml` against package entries in `uv.lock`.

This prevents a release from being treated as reproducible when a direct dependency is declared in the manifest but absent from the immutable lock.

## Verification

- Lock-gate unit tests: PASS 2/2.
- Non-billing regression: PASS 196/196.
- Full suite: PARTIAL/BLOCKED — 202 passed, 3 setup errors caused by missing `aiosqlite` in the host environment.
- Python compile: PASS.
- Secret scan: PASS (276 tracked files).
- Active-runtime n8n scan: PASS, 0 matches in runtime paths.
- Current R20 lock consistency: FAIL-CLOSED as designed; `asyncpg`, `psycopg`, and `redis` are declared but absent from `uv.lock`.
- `uv lock --check`: BLOCKED by the execution environment's package registry mirror, which cannot resolve `asyncpg`; public PyPI DNS is unavailable from this runtime.
- Ruff: BLOCKED, module unavailable.
- Bandit: BLOCKED, module unavailable.
- pip-audit: BLOCKED, module unavailable.

## Safety boundary

No secrets were exported or hardcoded. No production database or deployment was used. No external messages were sent. No paid OpenAI request was executed. The buyer-demo isolation boundary remains unchanged.

## Production decision

**NO-GO.** R21 closes a verification gap by making stale/incomplete dependency locks fail the release gate. Production readiness still requires a trusted network-enabled or pre-provisioned environment to regenerate `uv.lock`, install all locked extras, run the full suite plus Ruff/Bandit/pip-audit, and then execute the remaining authorized staging gates.
