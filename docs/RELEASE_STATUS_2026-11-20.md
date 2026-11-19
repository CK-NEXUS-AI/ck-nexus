# CK-NEXUS — Q10–Q16 Current Evidence Status

**Verification date:** 2026-11-20 (Asia/Bangkok)
**Repository:** `spinlnw10-art/ck-nexus`
**Candidate:** PR #387, commit `e4e804aa44ce71f5b4eea718266a07fd362b0a98`
**Candidate tree:** `e32c8d433a1f4a3e1aabd6f7e7e5225ea0fac08a`
**Runtime/release subject:** `aeedb59ed7b07e77cc57a899ab5445a8506817ce2cd34fd728269db12eb0f735`

> This document is the current status snapshot. It does not certify Production readiness. Historical evidence remains in the repository but must not be reused as proof for this candidate unless its source and runtime subject match this snapshot.

## Decision

**NO-GO — keep the candidate unmerged and undeployed.** The current CI and several component checks pass, but Q10 independent review and Q11 are unresolved, Q12 is blocked by the unavailable Linux runner, and Q13–Q16 are not all fully closed on one exact candidate. VPS-dependent work is intentionally left open for a later return of VPS access.

## Follow-up verification at the inspected PR head

After the baseline candidate snapshot above, PR #387 advanced to head 59bb346b65e8f33297e67d0f6d9f53298493151e. GitHub Actions runs on that PR head reported:

| Check | Run | Result | Interpretation |
|---|---:|---|---|
| Q10 Open-Source Layered Security Gate | [44598573684](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573684) | **SUCCESS** | Workflow success only; retain the independent-review requirement. |
| Q11 final release subject | [44598573958](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573958) | **FAILURE** | Log environment carried Q11_SOURCE_SHA=aac0b538516cd7777159f65fb7d0e0e588f1a5f2 and Q11_RELEASE_SUBJECT=aeedb59ed7b07e77cc57a899ab5445a8506817ce2cd34fd728269db12eb0f735; source provenance does not match the inspected PR head. |
| Q12 blocked-state recorder | [44598573516](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573516) | **SUCCESS (RECORDER ONLY)** | It successfully recorded the blocked state for the rotated subject. This is not a Q12 execution/pass. |
| Candidate automated gates | [44598573416](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573416) | **SUCCESS** | Q13/Q15 and related candidate components ran; candidate evidence only, not final release closure. |
| Q14 final release subject | [44598573512](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573512) | **SUCCESS** | Component workflow success; final provenance/package reconciliation remains required. |
| Candidate production image | [44598573668](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573668) | **SUCCESS** | Candidate artifact only, not a deployed production image. |
| Candidate runtime licenses | [44598573994](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44598573994) | **SUCCESS** | Candidate inventory only; bind to the final package after the subject is frozen. |

The PR checks also show SonarCloud Code Analysis FAIL. These follow-up runs do not change the release verdict: **NO-GO**. In particular, do not interpret a successful Q12 blocked-state recorder, candidate image build, or candidate component workflow as proof that the mandatory gate passed.

## Earlier Q-gate evidence found in the repository

These records are retained as historical candidate evidence. They do not certify the current PR #387 candidate because their source and subject differ from `e4e804a…` / `aeedb59…`.

| Gate | Recorded state | Evidence | Scope note |
|---|---|---|---|
| Q01–Q04 | **NOT VERIFIED IN CURRENT EVIDENCE SET** | No corresponding current tracked Q01–Q04 evidence record was identified in this inspection | No status is inferred or fabricated. Recover the original signed records if these gates are required. |
| Q05 | **PASS (historical candidate)** | Run `34926729111`; 598 tests passed / 0 failed; compile, Ruff, secret scan and Bandit-reviewed lane passed | Source `cd84d0d…`, tree `b0785a2…`, subject `bc77d4e…`; stale when subject changes. |
| Q08 | **PASS (historical candidate)** | Run `34926729111`; PostgreSQL and Redis live checks passed; concurrency single-winner, replay and live backend round trip verified | Same historical source/subject as Q05; rerun on final release subject if required. |
| Q09 | **PASS_CANDIDATE (historical candidate)** | Run `34926729111`; frozen sync, governance regression, live idempotency, PostgreSQL/Redis binding and quality lanes passed | Same historical source/subject; trusted identity required and unknown risk denied. Candidate evidence only. |

## Gate matrix

| Gate | Current state | Latest evidence | Remaining condition |
|---|---|---|---|
| Q10 security | **SCANNER PASS / WHOLE GATE NOT VERIFIED** | [Run 44591666442](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591666442), candidate `e4e804a…`; Bandit 0 HIGH / 0 MEDIUM / 520 LOW; pip-audit 0 vulnerabilities / 89 dependencies; secret scan PASS / 875 tracked files; attack regression 19/19 PASS | Independent Codex Security review is REQUIRED. Review/disposition the 520 LOW findings; do not interpret scanner PASS as security certification. `production_promotion_allowed=false`. |
| Q11 live provider | **BLOCKED** | [Run 44591665765](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665765), candidate `e4e804a…`; OpenAI Responses API returned HTTP 401 `invalid_api_key` | Replace the GitHub Actions `OPENAI_API_KEY` secret with a valid authorized project key and rerun the exact-subject gate. Never place the key in source, logs, issue text, or chat. |
| Q12 cgroup v2 | **BLOCKED — WAITING FOR VPS/HOST** | [Run 44591665760](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665760) recorded blocked state for the current candidate; `actual_kernel_enforcement=false`, `delegation_ready=false`; `cknexus-q12` runner offline | Restore a supported Linux host with delegated cgroup v2 and non-root enforcement, then rerun Q12 against the frozen subject. Android Termux cannot substitute. |
| Q13 PostgreSQL DR | **PASS_CANDIDATE** | [Candidate automated gates run 44591665667](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665667); backup/restore/sentinel round trip passed on staging candidate | Retain as candidate evidence only; rerun/verify on the final frozen release subject and preserve the complete artifact/provenance. |
| Q14 observability | **PASS (component)** | [Run 44591665756](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665756); alert delivery, health metrics, and failure injection passed; runtime subject matches `aeedb59…` | Reconcile source commit/provenance with the final candidate and include it in the final evidence package. Component PASS does not close the release. |
| Q15 clean machine | **PASS_CANDIDATE** | [Candidate automated gates run 44591665667](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665667); clean GitHub-hosted Ubuntu 24.04 install and smoke checks passed | This is candidate CI evidence, not proof of deployment on the future VPS/production host. Run the deployment-specific clean-host check when VPS is available. |
| Q16 production image | **PASS_CANDIDATE** | [Run 44591665933](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665933); image artifact built for candidate | Final image, runtime license inventory, final-tree checks, hashes, and release package must be regenerated/verified after Q10–Q15 closure. |
| Q16 runtime licenses | **PASS_CANDIDATE** | [Run 44591665714](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44591665714) | Confirm final artifact inventory/notices and bind to the final release package. |

## Important provenance correction

The tracked files `evidence/Q10_DEPENDENCY_AUDIT.json`, `Q11_OPENAI_LIVE.json`, `Q12_CGROUP_V2.json`, `Q13_POSTGRES_DR.json`, `Q14_OBSERVABILITY_ALERT.json`, `Q15_CLEAN_MACHINE.json`, and Q16 records still contain older source/subject values (`4cf17cd3…` / `96dcd0f0…`). They are historical snapshots, not evidence for candidate `e4e804a…` / subject `aeedb59…`.

There are historical Q12 PASS artifacts (runs `35421281024` from 2026-09-19 and `37416992838` from 2026-10-06). Those runs genuinely recorded `actual_kernel_enforcement=true` and `delegation_ready=true`, but their manifest subject is `96dcd0f0…`, not the current `aeedb59…`. Therefore they do **not** close Q12 for this candidate. The current Q12 run records BLOCKED.

The current `final-production-package.yml` and `verify/q12-final-subject` workflow configuration were previously found pinned to retired/intermediate subjects. They must be aligned to the final frozen subject only after the candidate is fixed and current-subject evidence is ready; do not change gate semantics or substitute old hashes to force a pass.

## Related checks and parallel provider work

- PR #387 is open and not merged. PR CodeQL passed for the changed code, but that does not clear existing `main` alerts.
- The latest recorded `main` code-scanning inventory was 152 open alerts (15 critical, 133 high, 4 medium); no alerts were dismissed as part of this work.
- SonarCloud analysis/check remains unresolved (cancelled/failed; authenticated Background Task details unavailable). Do not claim it passed.
- Gemini Live Smoke run [44586906717](https://github.com/spinlnw10-art/ck-nexus/actions/runs/44586906717) passed on separate draft PR #390. It does not satisfy the current Q11 contract, which explicitly tests the OpenAI Responses API. Provider-gate semantics must not be changed silently.
- The VPS device `vps3680569.trouble-free.net` is offline. No current VPS runtime, SSH, deployment, or end-to-end production verification is claimed.

## Work intentionally deferred until VPS returns

1. Restore or provision the supported Linux VPS/host and verify its identity and access.
2. Register/online the `cknexus-q12` runner; prove delegated cgroup v2 CPU, memory, and PID enforcement as a non-root service.
3. Re-run Q12 and every host-dependent Q13–Q16 check against one frozen candidate subject; collect raw artifacts and hashes.
4. Run Q15 deployment-specific clean-host install/health/smoke and Q16 final image/package verification on that host.
5. Reconcile all evidence manifests and `final-production-package.yml` with the same final source/tree/runtime subject; run the final provenance/package workflow.
6. Close Q10 independent review, Q11 live-provider failure, SonarCloud/required review items, then request final human approval.

## Safety and release controls

- Keep PR #387 open; do not merge, tag, deploy, or claim Production Ready while any required gate is blocked or not verified.
- Do not overwrite historical evidence with fabricated/current-looking PASS values. Preserve it as history and add new immutable, exact-subject evidence from real runs.
- No secret was read or changed; no production data was used; no VPS deployment was attempted in this update.

**Current release verdict: NO-GO.**
