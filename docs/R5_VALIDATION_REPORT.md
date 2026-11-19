# CK-NEXUS v0.2.0 R5 Validation Report

Status: **RELEASE CANDIDATE / NO-GO FOR PRODUCTION CLAIMS**

R5 adds the CK-NEXUS Development Council and repairs the PostgreSQL-only semantics of P0-EMAIL-001. This report records only evidence produced in the current build environment.

## Development Council

Implemented:

- `CK-NEXUS Lead Orchestrator` using the manager / agents-as-tools pattern.
- Five specialist adviser roles:
  - Architect & Strategist
  - Research & Analyst
  - Product & UX Designer
  - Engineering & Automation Builder
  - Security / QA / DevOps Reviewer
- `GET /api/dev-team`
- `POST /api/dev-team/run`
- `auto`, `council`, and five focused consult modes.
- Research-only hosted web-search surface.
- Per-adviser model override environment slots.
- `/demo` DEV TEAM workspace.
- Advisory-only policy: no specialist receives a mutation tool or direct external side-effect permission.

Local evidence:

- Development Council + Creator API targeted tests: **16/16 PASS**.
- Non-billing test suite after R5 changes: **40/40 PASS**.
- Full pytest run: **46 PASS / 3 ERROR**. The three errors are billing tests blocked by missing `aiosqlite` in this environment.
- Python compile: PASS.
- JavaScript syntax (`node --check`): PASS.
- R5 UI contract check: PASS.
- Worktree secret scan including tracked and untracked text files: PASS (139 text files at scan time).

Live multi-agent execution is **BLOCKED** in this environment because `OPENAI_API_KEY` is not present in the server runtime and the `openai-agents` package is not installed here. The secure OpenAI Platform key setup flow is separate from source control. No live Development Council claim is made.

## P0-EMAIL-001 repair

Previous mismatch: `runbooks/p0_runbook_v3.py` invoked `scripts/test_duplicate_concurrency.py --require-postgres`, but the script did not implement that flag and defaulted to SQLite when no database was supplied.

R5 changes:

- Added `--require-postgres`.
- Added `--database-url`, defaulting to `CKNEXUS_EMAIL_DATABASE_URL`.
- A required PostgreSQL run returns exit code `2` / BLOCKED if no PostgreSQL URL is configured.
- The concurrency key is unique for every run, so staging data from previous runs cannot invalidate the proof.
- The test counts journal rows for the exact `(mailbox, provider, provider_message_id)` key rather than the whole table.
- Added matching-row count support to both SQLite and PostgreSQL repositories.
- The P0 runbook now maps exit code `2` to BLOCKED for P0-EMAIL-001 instead of FAIL.

Local evidence:

- SQLite local proof: 100 attempts -> **1 winner / 1 matching journal row**; PASS as non-production evidence.
- `--require-postgres` without a PostgreSQL URL: **BLOCKED / exit 2** as intended.
- PostgreSQL 100-way runtime proof remains BLOCKED because Docker/PostgreSQL staging is unavailable in this environment.

## Release checker

Observed result:

- Required files: PASS
- Secret scan: PASS
- Python compile: PASS
- Test suite: FAIL only because 3 billing tests cannot import `aiosqlite`
- JavaScript syntax: PASS
- Ruff: unavailable
- Bandit: unavailable
- Dependency audit: unavailable
- Seller-only commercial files: optional/missing warning

## Environment blockers

- Docker: unavailable.
- `aiosqlite`: unavailable.
- Ruff: unavailable.
- Bandit: unavailable.
- pip-audit: unavailable.
- Server-side `OPENAI_API_KEY`: not present.
- OpenAI Agents SDK package: not installed in this runtime.

These are blockers to additional evidence, not reasons to promote the release status.

## Production boundary

R5 must remain Release Candidate until the required P0 gates pass on one exact source commit and one staging environment, including PostgreSQL concurrency, outbox timeout/retry, lease recovery, deployed n8n routing/audit, attachment quarantine, loop prevention, end-to-end correlation, backup/restore, live OpenAI AI001, security tooling, alert delivery, and clean-machine deployment.
