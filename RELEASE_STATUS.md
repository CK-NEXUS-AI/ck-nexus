# Release Status — CK-NEXUS Q10-Q16 Closure

Decision: **NO-GO FOR PRODUCTION CLAIMS**

Canonical main: `45fde79c717b09f8675645aa541a5834ebd4f433` (Q09)
Closure branch: `release/q10-q16-closure`
Frozen runtime/deployment subject: `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f`
Verified runtime source SHA: `4cf17cd3befaafeaf64cd4c149739133aa220f73`
Closure contract: `docs/Q10_Q16_CLOSURE_CONTRACT.md`

## Current release candidate

Unified Control and production hardening are converged on the closure branch but are **not merged to `main`**. The production image uses the exact `uv.lock`, a pinned Python base-image digest, pinned Compose service-image digests, a non-root runtime user, and `python -m creator_app.unified`. AGNES Phase3 defaults fail-closed (`false`) unless a real delegated cgroup v2 environment is explicitly provided.

## Gate matrix

| Gate | State | Evidence |
|---|---|---|
| Q05 quality/regression | PASS_CANDIDATE | 218/218 portable regression + compile/Ruff/Bandit-reviewed/secret scan PASS on the Unified application manifest |
| Q08 PostgreSQL/Redis live idempotency | PASS_CANDIDATE | live PostgreSQL + Redis PASS |
| Q09 governance binding | PASS_CANDIDATE | one-time capability grant, trusted identity required, unknown risk DENY |
| Q10 dependency component | **PASS** | run `31818388818`; `pip-audit` 0 vulnerabilities; artifact `9225932630` |
| Q10 whole security gate | **NOT VERIFIED / BLOCKER** | mandatory Codex Security Deep Security Scan has not run in the Codex Security workbench |
| Q11 live provider P0-AI-001 | **BLOCKED** | run `31818698368`; GitHub Actions `OPENAI_API_KEY` not configured; no credential exposed |
| Q12 delegated cgroup v2 | **BLOCKED** | run `31818756811`; hosted Ubuntu has required controllers but no writable non-root delegation boundary |
| Q13 PostgreSQL DR | **PASS_CANDIDATE** | run `31818388818`; backup + isolated restore + sentinel round-trip PASS |
| Q14 observability/operator delivery | **PASS** | run `31818646706`; production rule waited `for: 2m`, Prometheus → Alertmanager → staging operator webhook `firing`, health/metrics PASS |
| Q15 clean-machine deployment | **PASS_CANDIDATE** | run `31818388818`; fresh Ubuntu 24.04, frozen install, regression + Unified health/control smoke PASS |
| Q16 production image | **PASS_CANDIDATE** | run `31818388852`; frozen lock, pinned base, dependency check/imports, non-root, health/control PASS |
| Q16 runtime license inventory | **PASS** | run `31818388980`; 55 runtime distributions, 0 unresolved license-evidence entries |
| Q16 final merge/tag/package | **NOT ELIGIBLE** | blocked by Q10 whole gate + Q11 + Q12 |

## External blockers required before Production Ready

1. Run the repository-wide **Codex Security Deep Security Scan** for runtime subject `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f` and close/accept all reportable findings according to the security policy. Q10 remains NOT VERIFIED until that workbench evidence exists.
2. Securely configure an authorized staging `OPENAI_API_KEY` (GitHub Actions secret or equivalent secure runner secret) and rerun `verify/q11-final-subject`. Current evidence is BLOCKED, not FAIL.
3. Run `scripts/agnes_cgroup_v2_staging_gate.py` on a staging/self-hosted Linux service with explicit non-root writable cgroup v2 delegation for `cpu`, `memory`, and `pids`. GitHub-hosted runners do not provide the required delegation.

## Commercial status

The repository remains sellable as a **source-code / Release Candidate package without Production Ready claims**. Do not mark the artifact Production Ready, merge PR #14 to `main`, or create a production tag until the three blockers above are PASS and the final production package workflow succeeds.
