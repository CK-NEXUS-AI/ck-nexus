# Release Status — CK-NEXUS Q10-Q16 Closure

Decision: **NO-GO FOR PRODUCTION CLAIMS**

Canonical main: `45fde79c717b09f8675645aa541a5834ebd4f433` (Q09 baseline)
Closure branch: `release/q10-q16-closure`
Current closure head: `a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53`
Frozen runtime/security source SHA: `fe81c22da08913fd9fd9b37d4c80e459668e1362`
Frozen source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
Frozen runtime/deployment subject: `211a12d7b5759de7babdd882d2e527d5b6d1c1fe5ccec19084784232a44435f1`
Unified application subject: `dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec`
Closure contract: `docs/Q10_Q16_CLOSURE_CONTRACT.md`

This status follows the rotated closure authority recorded by commit `a55a8d36...`, the schema-v3 Q10 scan request, operator preflight, and final-production-package workflow. Older references to `96dcd0f0...` / `4cf17cd3...` are superseded for the current production-closure decision.

## Update 2026-09-15 — Post-P0 consolidation & rotated authority (automated housekeeping)

- Merged to main: #246, #240, #241, #242, #244, #245 (Post-P0 chain), #237 (Buyer Delivery V2 + Sonar fix), #230 (rotated closure authority reconciliation).
- Closed as duplicates/superseded: #226 (kept #227), #235 (kept #234), #236 (kept #237).
- Evidence Q05/Q08/Q09 regenerated for the current exact tree via `refresh-candidate-evidence` (runs 34926334985, 34926729111).
- CI on main: **CK-NEXUS CI PASS**. Q05: 598 passed / 0 failed. Q08 live: PostgreSQL PASS, Redis PASS.
- Buyer Delivery V2 (spec, packaging script, transfer schedule template, acceptance checklist) is on main; candidate ZIP built and validated in CI (run 34927478355, checksums OK, secret_scan PASS).
- Authority note: Q10-Q12 frozen authorities below follow the rotated closure authority (`a55a8d36...`); production-claims verdict stays NO-GO until gates move beyond PASS_CANDIDATE.
- Outstanding: remaining Post-P0 backlog PRs require rebase onto current main; #243/#250 CI unstable.

## Current release candidate

Unified Control and production hardening are converged on the closure branch but are **not merged to `main`**. The production image remains fail-closed and production eligibility is false while Q10, Q11, and Q12 are unresolved.

## Gate matrix

| Gate | State | Evidence |
|---|---|---|
| Q05 quality/regression | PASS | rotated-subject quality evidence on closure line |
| Q08 PostgreSQL/Redis live idempotency | PASS | rotated-subject live evidence on closure line |
| Q09 governance binding | PASS_CANDIDATE | governance binding on rotated subject |
| Q10 dependency component | **PASS** | run `31950497105`; artifact `9264500568`; `pip-audit` 0 vulnerabilities |
| Q10 whole security gate | **NOT_VERIFIED / BLOCKER** | open-source layered security scan and independent evidence review still required |
| Q11 live provider P0-AI-001 | **BLOCKED** | run `31950795711`; artifact `9264576887`; `OPENAI_API_KEY` not configured; no credential exposed |
| Q12 delegated cgroup v2 | **BLOCKED** | run `31950904091`; artifact `9264605328`; required self-hosted non-root delegated cgroup v2 enforcement has not executed |
| Q13 PostgreSQL DR | **PASS_CANDIDATE** | run `31950497105`; artifact `9264501762`; backup/restore + sentinel round-trip PASS |
| Q14 observability/operator delivery | **PASS** | run `31950773095`; artifact `9264602293`; alert delivery + health/metrics PASS |
| Q15 clean-machine deployment | **PASS_CANDIDATE** | run `31950497105`; artifact `9264502261`; fresh Ubuntu 24.04 + regression/smoke PASS |
| Q16 production image | **PASS_CANDIDATE** | run `31950497111`; artifact `9264502930`; non-root/frozen/runtime checks PASS |
| Q16 runtime license inventory | **PASS** | run `31950497135`; artifact `9264501377`; 55 runtime distributions; 0 unresolved license-evidence entries |
| Q16 final merge/tag/package | **NOT ELIGIBLE** | blocked by Q10 whole gate + Q11 + Q12 |

## Current Q10 authority

Canonical request: `evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json`

Required scan identity:

- target SHA: `fe81c22da08913fd9fd9b37d4c80e459668e1362`
- target tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- release subject: `211a12d7b5759de7babdd882d2e527d5b6d1c1fe5ccec19084784232a44435f1`
- scope: `.`
- mode: `layered`
- executor: **CK-NEXUS Open-Source Layered Security Gate**
- request state: **PREPARED_NOT_EXECUTED**
- production status: **NO-GO**

Q10 must not be promoted from any single scanner or ordinary CI alone. The replacement gate combines frozen dependency audit, Bandit, secret scanning, and black-box security regression. PASS requires a successful run ID, aggregate report SHA-256, completion timestamp, review/disposition of recorded findings, and exact release-subject provenance.

## External blockers required before Production Ready

1. Run the **open-source layered Q10 security gate** against the exact candidate commit; preserve full reports, review all medium/high findings, bind the aggregate report digest to the release subject, and regenerate all subject-bound evidence after any remediation.
2. Securely configure a seller/owner-authorized staging `OPENAI_API_KEY` through GitHub Actions secret or an equivalent secure runner secret and rerun the exact-subject Q11 verifier. Never place the raw credential in source, issue text, logs, or chat evidence.
3. Run `scripts/agnes_cgroup_v2_staging_gate.py` through the required self-hosted Linux runner labeled `cknexus-q12` with a writable non-root delegated cgroup v2 boundary for `cpu`, `memory`, and `pids`.

## Independent verification and release authority

- Native scanner evidence does **not** substitute for independent HUMAN review.
- Repository owner/AI must not self-approve the independent-review gate.
- Evidence should be hash-sealed and bound to exact subject/provenance before independent review.
- Owner HUMAN sign-off occurs only after independent review.
- PR #14 must remain governed and unmerged until all mandatory gates pass and the final production package succeeds.

## Commercial status

The repository remains sellable as a **source-code / Release Candidate package without Production Ready or Certified claims**. Do not mark the artifact Production Ready, create a production tag, or merge PR #14 to `main` until Q10, Q11, and Q12 are closed and the final production package workflow succeeds.
