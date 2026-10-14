# CK-NEXUS Q10–Q16 Evidence Triage — 2026-10-15

## Canonical source identity
- Repository: `CK-NEXUS-AI/ck-nexus`
- Main SHA observed: `cb612b72304246781b7dab48dad77d227c40d45d`
- Main tree observed in prior verified baseline: `20f2073aae91a586619e91bbfd33cc93ab9da872`
- Main was not modified during this audit.

## Q10 — Native security scan
- Existing evidence file `q10-status-20261007T042212Z.json` records `status=NOT_VERIFIED`, `result=SCAN_FAILED`, and `authentication_verified=false` for its recorded scan attempt.
- The record binds to older source commit `b96049db9ae206bdc2292108629d8583ea0277d`, not the currently observed main SHA.
- Supplemental tool findings do not substitute for the required native scan. Q10 remains **NOT_VERIFIED** for current release lineage.

## Q11 — Provider/runtime capability
- Existing signed closeout `Q11-CLOSEOUT-FINAL-20261008T052947Z.json` records production `NO-GO`; provider response was HTTP 429 / quota exhausted, authorization `NOT_VERIFIED`, and live execution `BLOCKED`.
- `q11-capability-gates-20261008T0315Z.json` records sub-gates A and C as VERIFIED, B as EXECUTED, D as NOT_VERIFIED, E/F BLOCKED, overall BLOCKED. Its recorded commit `91b39acfaaba392f7f3b5a7039fe76a299891286` is not the currently observed main SHA.
- Historical sub-gate evidence cannot close Q11 for current release lineage without a new bound verification.

## Q12 — Runtime isolation
- Read-only current cgroup checks show `cpu.max=max 100000`, `memory.max=max`, and `pids.max=max` under `/sys/fs/cgroup/cknexus-delegated`; these values do not demonstrate active resource limits.
- The Q12 runner service is active with `Delegate=yes`, but `User` is unset, `NoNewPrivileges=no`, `ProtectSystem=no`, `ProtectHome=no`, and `PrivateTmp=no` in the observed unit properties.
- Q12 runtime isolation is **NOT_VERIFIED**; do not interpret service-active as safe sandbox enforcement.

## Q13–Q16 — Release-bound evidence
- A filename inventory under `/opt/cknexus/evidence` found no files named with Q13, Q14, Q15, or Q16 in their filenames in the scanned evidence tree. This is an inventory observation, not proof that no relevant artifacts exist elsewhere.
- Prior project baseline says historical artifacts are not bound to one canonical release identity. No current release-bound evidence was established in this audit.
- Q13–Q16 remain **NOT_VERIFIED** for the current release until each gate is linked to the same immutable release identity and independently verified.

## Independent validation of isolated AI Product Factory patch
- Local-only patch adds explicit `-X GET` to `gh api search/repositories` and adds two regression tests.
- `uv run --with pytest --with pytest-asyncio --no-project -- python -m pytest -q tests/test_ai_github_harvester.py tests/test_ai_product_factory.py`: **7 passed**.
- Ruff on changed Python files: **All checks passed**.
- A read-only live API request with explicit GET succeeded and returned `total_count=2800` for the configured query at audit time. This validates endpoint/method behavior, not workflow execution or production readiness.
- The source patch and tests remain only in the isolated local working copy. No source code was pushed, no PR opened, no workflow triggered, and no deployment performed.

## Overall decision
- Q10: **NOT_VERIFIED**
- Q11: **BLOCKED / NOT_VERIFIED**
- Q12: **NOT_VERIFIED**
- Q13–Q16: **NOT_VERIFIED** for current release lineage
- Production: **NO-GO**

Next safe steps: obtain the required authorized native scan, resolve provider quota/authorization through owner-approved credentials, establish real cgroup resource limits and non-root delegation with owner review, and bind Q13–Q16 evidence to one canonical release. Do not promote based on historical artifacts or local tests alone.
