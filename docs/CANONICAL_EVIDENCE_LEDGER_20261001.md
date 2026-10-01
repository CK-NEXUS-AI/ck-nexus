# CK-NEXUS Canonical Evidence Ledger — 2026-10-01

## Purpose
Read-only-derived audit snapshot consolidating current observable repository and evidence facts.
Rules: Evidence before mutation; EXECUTED != VERIFIED; SHA MATCH != VERIFIED; LOCAL PASS != LIVE PASS; subject-bound evidence only; no secrets recorded.

## Repository identity
- Repository: spinlnw10-art/ck-nexus
- Repository ID: 1333067619
- Visibility: private
- Default branch: main
- Observed main HEAD: ba6eac66ac4efab2afff5bb9463d5ffd7a6fef76
- Observed main tree: 2745e38022e90198c56eb8d593a52179f27cdb0d
- Observed closure branch pointer: release/q10-q16-closure -> acda4055047b79d3c9e6ee1175c69fafcae49dc0
- RELEASE_STATUS.md names a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53 as closure head, but the live branch pointer is acda4055047b79d3c9e6ee1175c69fafcae49dc0.
- GitHub compare reports a55a8d36... and acda4055... as diverged: acda4055 is 4 commits ahead and 24 commits behind.

## Declared current release subject
- Frozen runtime/security source: 39f5c1adb9d761ab418cf088ff1f051b1ca731d1
- Frozen source tree: 0525195934f703a8becf8a39f6397b2411e0bb2e
- Release subject manifest: 89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52
- Application subject manifest: dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec

## Stale subject found in evidence
- Older source: 4cf17cd3befaafeaf64cd4c149739133aa220f73
- Older tree: dfe3888bb6adc9aebbb0351efe4a06006f4e0a48
- Older release subject: 96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f
- Multiple Q10-Q16 evidence records on the observed closure branch remain bound to this older subject.

## Gate ledger
| Gate | Observed evidence | Binding | Canonical disposition |
|---|---|---|---|
| Q05 | PASS evidence exists | candidate/subject-bound | PASS for its subject only |
| Q08 | PASS live evidence exists | candidate/subject-bound | PASS for its subject only |
| Q09 | PASS_CANDIDATE | subject-bound | PASS_CANDIDATE |
| Q10 dependency | pip-audit 0 vulnerabilities | old subject in observed record | component PASS only; whole gate NOT_VERIFIED |
| Q10 whole | native Codex deep scan required | request says PREPARED_NOT_EXECUTED | NOT_VERIFIED / BLOCKER |
| Q11 | run 31950795711 failed; credential not configured; sentinel absent | exact closure evidence not closed | BLOCKED |
| Q12 | run 35421281024 succeeded; actual cgroup enforcement true | evidence record bound to old 96dcd0... subject | NOT PROMOTED to current release |
| Q13 | backup/restore and sentinel round-trip PASS | old subject | PASS_CANDIDATE for old subject only |
| Q14 | alert delivery and health/metrics PASS | old subject | PASS for old subject only |
| Q15 | clean-machine smoke PASS | old subject | PASS_CANDIDATE for old subject only |
| Q16 image | non-root/import/health smoke PASS | old subject | PASS_CANDIDATE for old subject only |
| Q16 licenses | 55 runtime distributions, no unresolved license evidence | old subject | PASS for old subject only |
| Production | release status says NO-GO | mandatory gates unresolved | NO-GO |

## Q10 proof
- Q10 dependency evidence records pip-audit exit code 0 and zero vulnerabilities.
- The same record explicitly says the native Codex Security Deep Security Scan is required separately and gate_result is NOT_VERIFIED.
- The Q10 request requires exact target 39f5c1..., tree 052519..., scope '.', deep mode, validation and attack-path phases, generated report, coverage, scan ID, report SHA-256, and completion timestamp.
- No completed native Codex scan evidence satisfying those fields was observed.

## Q11 proof
- Workflow run 31950795711 completed with failure.
- Committed evidence records credential_configured=false, credential_exposed=false, sentinel_observed=false, and P0-AI-001 BLOCKED.
- No credential value is recorded in this ledger.

## Q12 proof
- Workflow run 35421281024 completed with success.
- Q12 evidence reports actual kernel enforcement true, delegated cgroup v2 ready true, cpu/memory/pids controllers, exit code 0, and result PASS.
- However, that evidence is bound to the older 96dcd0... release subject and older source 4cf17cd3..., so it cannot close the current 89f2925... release subject without an exact-subject refresh.

## Critical reconciliation finding
The largest current evidence-integrity issue is subject/branch/evidence divergence, not absence of tests.

1. main currently points to ba6eac66....
2. release/q10-q16-closure currently points to acda4055....
3. RELEASE_STATUS.md names a55a8d36... as closure head.
4. a55a8d36... exists and is GitHub-verified, but is not the current closure branch tip.
5. a55a8d36... and acda4055... are diverged.
6. Some evidence uses release subject 89f2925..., while other evidence uses 96dcd0f....
7. Q12 has a later successful execution, but its committed evidence is still bound to the old subject.

Verdict: a single production-release evidence truth is NOT YET ESTABLISHED. This ledger therefore remains RECONCILIATION_REQUIRED.

## Required next evidence operations
1. Freeze one intended release authority: exact ref, source SHA, tree, release subject and application subject.
2. Reconcile the live closure branch pointer against RELEASE_STATUS.md.
3. Refresh every mandatory gate whose evidence is stale or subject-mismatched.
4. Execute the required native Codex Security Deep Security Scan for the frozen Q10 subject.
5. Run Q11 with owner-authorized staging credentials through a secure secret mechanism; preserve sentinel evidence without exposing the key.
6. Re-run Q12 on the exact frozen subject and bind the resulting evidence to that subject.
7. Reconcile Q13-Q16 to the same subject when required by the final release contract.
8. Only after all mandatory evidence is subject-consistent should production-release eligibility be reconsidered.

## Safety status
- Production claim: NO-GO
- Production tag: DO NOT CREATE
- PR #14: DO NOT MERGE until mandatory gates and final package succeed
- Secrets: none recorded
- Destructive cleanup: none performed by this ledger operation
- This ledger does not close any Q gate.

## Source files
- RELEASE_STATUS.md
- docs/Q10_Q16_CLOSURE_CONTRACT.md
- docs/RELEASE_EVIDENCE_PROVENANCE.md
- evidence/Q10_DEPENDENCY_AUDIT.json
- evidence/Q11_OPENAI_LIVE.json
- evidence/Q12_CGROUP_V2.json
- evidence/Q13_POSTGRES_DR.json
- evidence/Q14_OBSERVABILITY_ALERT.json
- evidence/Q15_CLEAN_MACHINE.json
- evidence/Q16_PRODUCTION_IMAGE.json
- evidence/Q16_RUNTIME_LICENSE_SUMMARY.json
- evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json

Generated from read-only GitHub observations on 2026-10-01. Audit snapshot only; not release authorization.