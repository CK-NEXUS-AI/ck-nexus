# Release Status — CK-NEXUS Creator Edition v0.2.0 R4

Decision: **RELEASE CANDIDATE / NO-GO FOR PRODUCTION CLAIMS**

R4 is an Integration Hub and delivery-hardening iteration built on the immutable `v0.2.0-p0-rc` baseline. It does not replace the P0 staging evidence requirement.

## R4 implemented

- Unified Integration Hub API for GitHub, Slack, Google Drive, n8n, OpenAI configuration, and database reachability.
- Full System Demo SYSTEM matrix expanded with server-side integration states.
- Secrets remain server-side and are not returned by integration status endpoints.
- Default OpenAI API model normalized to `gpt-5-mini`; `OPENAI_MODEL` override remains supported.
- GitHub Actions CI added for compile, Ruff, Bandit, secret scan, and pytest.
- Weekly/manual dependency audit workflow added.
- Release checker no longer crashes when seller-only commercial files are absent from the source repository.
- `.env.p0.example` and `.env.prod.example` are now intentionally tracked examples while real `.env*` secrets remain ignored.

## Locally verified in this build environment

- Python compilation: PASS
- Non-billing regression: **35 passed**
- Integration Hub tests: PASS within the non-billing regression set
- JavaScript syntax (`node --check`): PASS
- Tracked-file secret scan: PASS
- `/health`: HTTP 200
- `/api/status`: HTTP 200
- `/api/integrations/status`: HTTP 200
- `/demo`: HTTP 200
- Git diff whitespace check: PASS

## Local validation blockers

These are environment/tooling blockers, not production PASS evidence:

- Billing tests: 3 tests cannot execute here because `aiosqlite` is not installed and package installation is unavailable in this runtime.
- Ruff: unavailable in this runtime.
- Bandit: unavailable in this runtime.
- pip-audit: unavailable in this runtime.

The GitHub CI workflow installs `.[dev,billing,email]` and is intended to run the complete suite once the repository is available.

## Production P0 blockers still open

- PostgreSQL concurrency/dedup evidence on staging.
- Outbox timeout/retry and lease-recovery evidence on staging.
- Actual n8n workflow execution/routing evidence and `n8n audit`.
- Attachment quarantine and loop-prevention evidence through the deployed pipeline.
- Backup/destroy/restore/boot evidence.
- Live OpenAI production-path smoke evidence (AI001).
- Real security tooling evidence (gitleaks/Bandit/dependency audit as applicable).
- Observability/alert delivery after failure injection.
- Clean-machine deployment from the exact release artifact.
- Final commercial/legal package completion before sale close.

Do not label this build `Production Ready` until the required P0 gates pass against one exact commit and environment.
