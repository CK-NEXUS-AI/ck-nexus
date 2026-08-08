# Release Status — CK-NEXUS Creator Edition v0.2.0 R7

Decision: **DEVELOPMENT CANDIDATE / RELEASE CANDIDATE / NO-GO FOR PRODUCTION CLAIMS**

R7 continues from R6 Autonomy Hardening and cuts the provider-routing primitive into the real CreatorRuntime and Development Council. It also introduces the first Credential Broker boundary, Gmail OAuth flow, and GitHub App installation-token path. It does not replace any staging P0 evidence requirement.

## R7 implemented

- Least-privilege Credential Broker with explicit consumer policies, consumer-bound secret leases, ephemeral runtime token storage, and redacted status/repr.
- Mock / loopback-only Ollama / broker-backed OpenAI adapters.
- Provider Router integrated with CreatorRuntime and Development Council; OpenAI Agents SDK failures/successes update the R6 circuit breaker.
- Council remains true five-specialist + lead-orchestrator execution on an Agents-SDK-capable provider; it fails closed instead of representing a single Ollama response as a five-agent council.
- OpenAI Agents SDK tracing keeps workflow observability while setting `trace_include_sensitive_data=False` for these runtime paths.
- Gmail OAuth server flow: one-time state, offline access, `gmail.readonly` default, optional `gmail.send`, tokens retained only inside the broker in this slice.
- GitHub App JWT/installation-token path with short-lived broker-only installation tokens and optional `PyJWT[crypto]` dependency.
- New redacted status endpoints for providers/credentials plus Gmail OAuth and GitHub App integration endpoints.

## Production blockers retained / added

- Gmail refresh-token storage is **ephemeral-memory only** in R7; production requires an encrypted durable vault and rotation/revocation procedure.
- GitHub App must be registered/installed and exercised against the intended repository with least-privilege permissions.
- Live OpenAI AI001 and optional Ollama runtime evidence are not claimed by unit tests.
- PostgreSQL concurrency, n8n execution/audit, backup/restore, observability/alert delivery, clean-machine deployment, and remaining P0 gates are still open unless separately evidenced against this exact release.

## Claim discipline

Passing unit/regression tests proves code-path behavior only. It does not make this build Production Ready. Critical FAIL or BLOCKED staging gates keep the overall release at NO-GO.

## Local R7 validation

- Non-billing regression: **89 passed**.
- Full pytest: **95 passed / 3 billing errors** (`aiosqlite` missing).
- Python compile: PASS.
- JavaScript syntax: PASS.
- Whole-worktree secret-pattern scan: PASS.
- Ruff/Bandit/pip-audit: BLOCKED because the binaries are unavailable in this runtime.
- Fresh offline uv resolution: BLOCKED by missing `asyncpg` cache for supported platform splits.
