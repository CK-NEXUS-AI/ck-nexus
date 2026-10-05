# CK-NEXUS Free Closure — 2026-10-02

## Canonical engineering target

- Repository: `spinlnw10-art/ck-nexus`
- Base: `main`
- Closure branch: `closure/one-shot-evidence-closure-20261002`
- Closure HEAD after evidence binding: `546797016270865cff47eccafdb30f04158ab088`
- Verified runtime/security subject SHA: `aa362faf16eaf5f3c2721491332cbed0266b4727`
- Verified runtime/security subject tree: `3fbc7c4994546e76c6360cbf26f42140c373fb7d`
- Subject manifest: `4da11963ea9b4adcbe5d72d7a0b4b0fef533da25fdd576a428059a2cbf3a5a61`
- Pull request: #252

## Engineering changes completed on the closure branch

1. Refreshed the trusted-verifier base-image pin to the digest observed by GitHub-hosted runners.
2. Fixed the trusted verifier runner import path so workspace packages resolve inside the verifier container.
3. Raised vulnerable dependency floors for `httpx2` and `PyJWT`.
4. Refreshed `uv.lock`; current locked versions observed:
   - `httpx2 2.13.1`
   - `httpcore2 2.13.1`
   - `PyJWT 2.15.1`
   - `urllib3 2.8.0`
5. Removed the one-time dependency-refresh workflow after the lock was committed.
6. Rebound Q05/Q08/Q09 evidence to the verified runtime/security subject.
7. Preserved the existing fail-closed Bandit reviewed gate and historical evidence.

## Current verified CI evidence

Latest verified subject workflow runs:

- Refresh candidate evidence: `36950904249` — PASS
- CK-NEXUS CI: `36951050805` — PASS
- Security Attack Regression V1: `36951050810` — PASS
- Trusted Verifier Image CI: `36951050820` — PASS
- Universal System Post-P0 CI: `36951050881` — PASS

CK-NEXUS CI evidence:
- Q04 frozen sync: PASS
- Compile/Ruff: PASS
- Bandit exact reviewed gate: PASS; `blocking=[]`
- Secret scan: PASS
- Portable regression: PASS
- Exact-tree evidence validation: PASS

Refresh evidence run `36950904249`:
- Q05: PASS
- Q08: PASS
- Q09: PASS_CANDIDATE
- 598/598 Q05 regression tests passed
- Q08 PostgreSQL live: PASS
- Q08 Redis live: PASS
- Q08 concurrency/single-winner/replay/live round-trip: PASS
- Q09 governance, binding, fail-closed unknown-risk and grant-consumption checks: PASS

## Dependency security finding resolved

An earlier Security Attack Regression run identified 22 vulnerable dependency findings in the resolved development environment. The lock was refreshed after raising dependency floors. The resulting lock now resolves the reported vulnerable packages above their reported fix versions.

The repository's own latest Security Attack Regression for the closure subject is PASS.

## Trusted verifier

Trusted Verifier Image CI now passes end-to-end on the closure subject, including:
- exact pinned base-image check
- verifier image build
- runtime isolation smoke
- provenance path

The previous failures were caused first by stale base-image digest pinning and then by the verifier not putting `/workspace` on `PYTHONPATH`. Both repository-controlled defects were corrected.

## Q05/Q08/Q09 evidence lineage

Evidence is bound to the same runtime/security subject:

- source SHA: `aa362faf16eaf5f3c2721491332cbed0266b4727`
- source tree: `3fbc7c4994546e76c6360cbf26f42140c373fb7d`
- subject manifest: `4da11963ea9b4adcbe5d72d7a0b4b0fef533da25fdd576a428059a2cbf3a5a61`
- validation run: `36950904249`

The later closure commits only changed evidence/documentation/CI-support paths outside the runtime subject, so the exact subject manifest remains stable.

## External / authority-bound blockers

### Q10 — Whole security gate
**NOT_VERIFIED**

The repository requires native repository-wide Codex Security Deep Security Scan provenance for Q10. The GitHub PR's Codex review integration has reported that the available Codex code-review usage limit has been reached. No replacement scan has been fabricated.

### Q11 — Live provider verification
**BLOCKED**

The required owner-authorized `OPENAI_API_KEY` is not configured in the required secure runner context. Existing Q11 evidence remains BLOCKED. No credential was placed in source, issues, logs, or this report.

### Q12 — Delegated cgroup v2
**BLOCKED**

The required non-root self-hosted Linux environment with writable delegated cgroup v2 enforcement for the required controllers is not available. Existing Q12 evidence remains BLOCKED.

### SonarQube Cloud
**NOT_VERIFIED / EXTERNAL**

The SonarQube Cloud check for PR #252 reported an external analysis failure/cancellation. The connector available here does not expose the underlying Sonar analysis diagnostics or credentials needed to repair the external analysis configuration, so no Sonar PASS is claimed.

## Actions usage

Workflow run count is not an Actions-minute measurement.

`ACTIONS_USAGE = NOT_VERIFIED`

## Production boundary

**PRODUCTION = NO-GO**

Engineering CI closure does not establish production certification. Q10, Q11, Q12 and independent human review remain required before any production-ready claim, production release/tag, or governed merge of the production closure.

## Final engineering status

**PARTIALLY_VERIFIED**

Verified:
- dependency lock/security-floor remediation
- Bandit reviewed gate
- secret scan
- regression suite
- Q05
- Q08
- Q09 candidate evidence
- trusted verifier
- attack regression
- Universal System Post-P0 CI

Not verified / blocked:
- Q10 native Codex deep security authority
- Q11 live provider credential verification
- Q12 delegated cgroup-v2 staging verification
- SonarQube Cloud analysis
- independent human release authority
