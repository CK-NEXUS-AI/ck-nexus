# CK-NEXUS Free Closure — 2026-10-02

## Canonical engineering target

- Repository: `spinlnw10-art/ck-nexus`
- Base: `main`
- Closure branch: `closure/one-shot-evidence-closure-20261002`
- Main baseline at closure start: `ba6eac66ac4efab2afff5bb9463d5ffd7a6fef76`
- Subject manifest: `bc77d4edf8615762fbb38331ea954f0ed5e3c44b3bc4a6df676410048685c45a`

## Changes executed

1. Trusted verifier base-image pin updated from the stale digest to the currently observed `python:3.12-slim-bookworm` index digest:
   `sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e`.
2. Candidate evidence refresh workflow enabled for this closure branch only.
3. Q05/Q08/Q09 evidence regenerated from GitHub Actions run `36950511678`.
4. Historical evidence was not deleted or overwritten on `main`.

## CI/security evidence

Refresh run: `36950511678`

- Frozen environment: PASS
- Q05 quality lanes: PASS
- Bandit reviewed gate: PASS; `blocking=[]`
- Secret scan: PASS (595 tracked files)
- Regression: 596 passed, 2 skipped, 1 warning
- Q09 governance regression: PASS
- Q06/Q07 application binding: PASS
- Q08 live idempotency: PASS
- PostgreSQL live: PASS
- Redis live: PASS
- Q08 concurrency/replay/live-backend properties: PASS

The earlier Bandit diagnosis is superseded by current evidence: the current CI Bandit gate is passing. The old failing runs were not evidence of a current Bandit failure.

## Q05/Q08/Q09 lineage

All three regenerated artifacts are bound to:

- source SHA: `4d147fa4d46c90e2be69013e186cab140308ad94`
- source tree: `bb5dedc3a4140039b03fcfab51eb4ec2616bca35`
- subject manifest: `bc77d4edf8615762fbb38331ea954f0ed5e3c44b3bc4a6df676410048685c45a`
- GitHub run: `36950511678`

Q05 = PASS.
Q08 = PASS.
Q09 = PASS_CANDIDATE.

## Trusted verifier

Previous failure evidence showed exact base-image drift:

- pinned: `python@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134`
- resolved: `python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e`

The closure branch updates the pin to the resolved digest. Final PASS still requires the PR trusted-verifier workflow to execute successfully.

## Q10/Q11/Q12

These remain separate external-authority gates and are not falsely promoted:

- Q10 whole security gate: NOT_VERIFIED; native repository-wide Codex Security Deep Security Scan remains required.
- Q11: BLOCKED; owner-authorized `OPENAI_API_KEY` is not configured in the required secure runner context.
- Q12: BLOCKED; required non-root self-hosted Linux cgroup-v2 delegation environment is unavailable.

Existing evidence for these blockers remains authoritative until a new exact-subject run closes them.

## Actions usage

A workflow run count is not an Actions-minute measurement. Billing/minute usage is not asserted here: `ACTIONS_USAGE = NOT_VERIFIED`.

## Production boundary

Production remains NO-GO.

This closure branch is an engineering/evidence closure candidate, not production certification. Q10/Q11/Q12 and independent human review remain mandatory before any production-ready claim, release tag, or merge of the governed production closure.

## Status

Current branch status: **PARTIALLY_VERIFIED**

Verified on this branch:
- CI/security quality lanes
- Q05
- Q08
- Q09 candidate evidence
- trusted-verifier pin correction pending final PR CI

Blocked/not verified:
- Q10 native deep security authority
- Q11 live provider credential verification
- Q12 delegated cgroup-v2 staging verification
- production certification
