# CK-NEXUS R6 Autonomy Hardening — Development Candidate

This work continues from R5 Development Council commit
`dca89ffed25e421030ae3fb88717a80b39bb8141` without changing the R5 production
claim. The system remains a Release Candidate / NO-GO until the existing staging
P0 gates have runtime evidence.

## Implemented in this development slice

- Provider routing primitive with deterministic local/mock-first ordering, optional
  cloud fallback, capability filtering, bounded attempts, and an in-memory circuit
  breaker/cooldown.
- Integration URL hardening for credential-bearing Slack, Google Drive, and GitHub
  calls: HTTPS-only, exact trusted-host checks, userinfo/query/fragment validation,
  and redirects disabled before an Authorization header is sent.
- Production fail-closed startup for CK-NEXUS access authentication. When the Email
  Gateway is enabled in production, its webhook secret is also mandatory.
- Split `/health/live` and `/health/ready` probes with structured dependency cause
  codes. The existing `/health` endpoint is preserved for compatibility.
- Reliability primitives for deterministic recovery, isolated repair, test/security
  gates, canary validation, bounded repair attempts, and rollback. The repair policy
  explicitly forbids direct production mutation and privileged/Docker-socket access.

## Deliberate boundaries

- The new provider router is a tested routing primitive; R5 CreatorRuntime and the
  Development Council still use their existing runtime path. Provider adapters and
  runtime cutover are a later integration slice.
- The repair policy is a safety state machine, not a privileged production executor.
- Gmail OAuth account connection and GitHub App credential minting are not implemented
  by this slice.
- No live OpenAI or third-party provider request was made for this development work.

## Local validation

- Non-billing regression: 74 passed.
- New/changed reliability and integration modules: Ruff PASS.
- Python compile: PASS.
- `git diff --check`: PASS.
- Whole-worktree secret-pattern scan including untracked source files: PASS.
- Full billing suite: BLOCKED in this environment because the required SQLAlchemy
  package is not available in the offline dependency cache.

## Next P0 integration slice

1. Add concrete local and OpenAI provider adapters and route CreatorRuntime through
   the provider router while preserving `/api/runs` compatibility.
2. Add a credential broker with opaque references and encrypted-at-rest production
   backend; move long-lived environment credentials behind that boundary.
3. Implement Gmail OAuth for an existing user-owned account and GitHub App
   installation-token refresh. Never accept Gmail passwords or OTPs.
4. Feed readiness/provider metrics into the external watchdog and alerting stack.
5. Exercise repair/canary/rollback against an isolated staging deployment and retain
   correlated evidence before changing the production readiness claim.
