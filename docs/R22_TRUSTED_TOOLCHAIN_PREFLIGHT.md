# CK-NEXUS R22 Trusted Toolchain Preflight

Baseline: R21 Lock Consistency Gate, commit `89eac80e055e91e018f596d2b1f8f8caf82099cc`, tag `v0.2.0-r21-lock-consistency-dev.1`.

## Increment

R22 adds a fail-closed trusted-toolchain readiness gate and makes it a required release check. The gate checks whether the configured package registry host resolves and whether the required runtime/security modules are importable. It intentionally reports only the registry hostname, never the complete registry URL, because package-index URLs can contain credentials.

Required modules checked by the gate: `aiosqlite`, `asyncpg`, `psycopg`, `redis`, `ruff`, `bandit`, and `pip-audit`.

## Verification

- R21 ZIP SHA-256: verified against immutable evidence.
- R21 Git bundle: verified as complete history; R21 branch/tag resolve to commit `89eac80e055e91e018f596d2b1f8f8caf82099cc`.
- Trusted-toolchain + lock-gate tests: PASS 4/4.
- Non-billing regression: PASS 198/198.
- Billing tests: PARTIAL/BLOCKED — 6 passed / 3 setup errors because `aiosqlite` is not installed.
- Python compile: PASS.
- Secret scan: PASS (279 tracked files before this commit).
- Active-runtime n8n scan: PASS, 0 matches.
- Current lock consistency: FAIL-CLOSED; `asyncpg`, `psycopg`, and `redis` remain missing from `uv.lock`.
- Trusted toolchain readiness: FAIL-CLOSED; required modules are unavailable in this validation environment.
- `uv lock` through the configured internal mirror: BLOCKED because the mirror cannot resolve `asyncpg`.
- `uv lock --index-url https://pypi.org/simple`: BLOCKED because public PyPI DNS/network access is unavailable.

## Safety boundary

No production database or production deployment was used. No external messages were sent. No paid OpenAI request was executed. No application secret was exported or hardcoded. Buyer-demo isolation behavior is unchanged, and active n8n runtime remains absent.

## Production decision

**NO-GO.** R22 improves release safety and diagnostics but does not close the trusted dependency/toolchain gate. The exact blocker is access to a trusted registry or pre-provisioned package set containing the declared dependencies and security tools.
