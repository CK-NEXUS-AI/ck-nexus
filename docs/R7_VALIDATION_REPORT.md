# CK-NEXUS R7 Validation Report

Release posture: **Development Candidate / Release Candidate / NO-GO for Production claims**

Baseline: R6 commit `4603d45acdbde13491582c7a6f85570372035c86` on `r6-autonomy-hardening`.
R7 branch: `r7-credential-broker`.

## Verified locally in this environment

- Provider/Credential/Gmail/GitHub App targeted tests: PASS.
- Non-billing regression: **89 passed**.
- Full pytest: **95 passed / 3 errors**; all three errors are billing tests blocked because `aiosqlite` is not installed.
- Python compilation: PASS.
- JavaScript syntax for both web entrypoints: PASS.
- `git diff --check`: PASS.
- Whole-worktree secret-pattern scan including untracked R7 files: PASS.
- `uv.lock` TOML parse: PASS; root package metadata includes `github-app` optional extra and the already-locked `PyJWT[crypto]` dependency.

## Tool/environment blockers

- Ruff binary: unavailable in this runtime.
- Bandit binary: unavailable in this runtime.
- pip-audit binary: unavailable in this runtime.
- `uv lock --check --offline`: BLOCKED because the offline cache does not contain `asyncpg` for every supported Python/platform split; this environment cannot perform a fresh all-platform resolution.
- Billing tests: BLOCKED by missing `aiosqlite`.
- Docker/PostgreSQL staging: not evidenced by this local unit run.

## R7 security assertions verified by tests

- Credential leases are consumer-bound and redact secret values from `repr`.
- Credential status API returns configuration metadata only, never credential values.
- Ollama base URL rejects non-loopback hosts and embedded user credentials.
- OpenAI adapter receives its key from the broker rather than returning it through status.
- Gmail OAuth authorization URL does not contain client secret; state is one-time; mocked token exchange stores access/refresh tokens only inside the broker.
- GitHub App mocked installation-token exchange stores the token only inside the broker and returns safe status.
- CreatorRuntime and Development Council report OpenAI success/failure back to the R6 circuit breaker.
- OpenAI Agents SDK runtime paths disable sensitive payload inclusion in traces.

## Not production evidence

The mocked OAuth/App tests do not prove external account connectivity. R7 still needs durable encrypted credential storage, live Gmail OAuth refresh/revocation evidence, live GitHub App installation evidence, AI001, and all inherited P0 staging gates before Production Ready can be claimed.
