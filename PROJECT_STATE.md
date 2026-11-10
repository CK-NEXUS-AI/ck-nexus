# CK-NEXUS — PROJECT STATE

> Snapshot generated: 2026-11-10T09:10:41Z
> State class: OBSERVED SNAPSHOT — not a production release approval
> Refresh trigger: every commit/branch change, Q-gate run, PR state change, or agent handoff
> Authority: CK-NEXUS Core / L3 remains the sole authority for state, permissions, policy, execution and evidence.

## 1. Canonical source identities

| Context | Identity | Notes |
|---|---|---|
| GitHub `main` | commit `4d1366cef3cbdd18aa174bdf67308567635c750a`; tree `57adfe86cd6d9bdbca5c97d336cb733df2308ae5` | Latest `main` SHA observed during this snapshot |
| Q10–Q16 closure candidate | branch `closure/q10-q16-unification-20261105`; commit `13cf6e1b2744c796dda85052b2b92a65e570536c`; tree `58d490d1bd670d3cbdbb3302c2b5972155869fe5` | PR #354; keep separate from `main` |
| Candidate manifest subject in runbook | `5129fa855515a13484e9e0e1816eef219f061dd87cc0651eaffae87096741147` | Expected subject recorded in candidate runbook/manifest |
| Subject computed by Q10/Q11/Q12/Q14/Q16 candidate workflows | `eb0e2a06365ed9166e05a249723df11f2fa4bfd51990b8de056f8f6b1897ce81` | MISMATCH — release-subject reconciliation is a blocker; do not rewrite expected SHA to force a match |
| VPS worktree `/root/ck-nexus` | branch `feature/autonomous-brain-foundation`; HEAD `9a6d8f2a05bf412940389e7c6084cac1140fec40` | Local-only state; not the closure candidate |

Never reuse evidence from older candidate subjects (including PR #341 or previous closure baselines) as evidence for the current candidate.

## 2. Q10–Q16 candidate status

Evidence source: GitHub Actions runs attached to candidate commit `13cf6e1b2744c796dda85052b2b92a65e570536c`, observed 2026-11-10.

| Gate | Latest observed result | Run | Interpretation / blocker |
|---|---|---:|---|
| Q10 | FAIL / NOT_VERIFIED | `42785906155` | Scanner execution completed and 10/10 reports exist; open-source security assessment rejected: 22 Semgrep security ERROR findings; Bandit reported 534 LOW findings; independent review and Owner approval pending. No production promotion. |
| Q11 | BLOCKED | `42786009668` | Credential is configured but live provider smoke did not return the required sentinel; diagnostic indicates credential rejected/expired. Credential was not exposed. |
| Q12 | PASS at runtime test; release reconciliation BLOCKED | `42786013880` | Real delegated cgroup v2 enforcement observed: `cpu.max=20000 100000`, `memory.max=67108864`, `pids.max=16`, `actual_kernel_enforcement=true`. Evidence subject hash is `eb0e…`, not the expected `5129…`; do not claim final Q12 closure until reconciled. |
| Q13 | NOT RUN / no candidate evidence observed | — | Run the PostgreSQL backup/restore and recovery verification on the exact candidate in isolated staging. |
| Q14 | Workflow PASS | `42786018478` | Candidate workflow completed successfully; bind and reconcile its evidence to the authoritative release subject before counting it as closed. |
| Q15 | NOT RUN / no candidate evidence observed | — | Perform clean-host installation and acceptance test using the exact candidate artifact. |
| Q16 image | FAIL | `42786023984` | Production image scan reports 1 HIGH and 1 MEDIUM gate-level finding; full scan summary reports 49 HIGH and 75 MEDIUM. Medium review is pending; image gate did not pass. |
| Q16 runtime licenses | PASS | `42786028924` | License inventory workflow passed; this does not override the failed image gate or close Q16 as a whole. |

All listed workflow runs use source SHA `13cf6e1…` and source tree `58d490…`. CI green on other workflows is not proof that mandatory release gates pass.

## 3. Active PR map

| PR | State at snapshot | Work |
|---:|---|---|
| #354 | OPEN | Exact Q10–Q16 closure candidate; primary release-closeout thread |
| #359 | OPEN | GHAS / CodeQL security remediation |
| #360 | OPEN | AGNES Sentinel evidence auditor |
| #361 | OPEN, DRAFT | AGNES external capability registry review |
| #355 | OPEN | Commercial value and go-to-market roadmap |
| #346 | MERGED | Fail-closed multi-channel brain ingress contract |
| #353 | MERGED | Canonical runtime entrypoint unification |

PR #354 must not be merged while mandatory gates or exact-subject reconciliation remain unresolved. Do not merge/deploy Production based on this snapshot.

## 4. AGNES skills and Project Observatory

- The system-skills harvest catalog contains 31 candidate skills: reuse/extend/new-skill/evaluate/blocked-by-evidence decisions. It is a discovery/admission input, not proof that every skill is installed or active.
- The external capability registry is represented by draft PR #361; external capabilities remain `authority_level=NONE` unless admitted by CK-NEXUS Core policy.
- Multi-channel ingress contract PR #346 is merged; actual channel adapters and live end-to-end operation still require independent verification.
- Project Observatory is a proposed shared intelligence layer: file inventory + architecture map + dependency graph + symbol index + work ledger + evidence index. `ast-outline`, `@munero/cindex`, Vibe Splain, semtree and Plandex have not been verified as installed on the VPS in this snapshot. Do not install them before checking current inventory and runtime requirements.
- Plandex is an execution assistant only; it is not a Q10–Q16 judge or L3 authority.

## 5. VPS and worktree observations

- VPS device `vps3680569` was reachable through the authorized remote-control connector during this snapshot.
- Q12 runner service `actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service` was stopped and disabled after the Q12 test. Do not assume it is online now.
- `/root/ck-nexus` is on `feature/autonomous-brain-foundation` at `9a6d8f2…`; status showed ahead 1 and two untracked files: `docs/VPS_BROWSER_DEPLOYMENT_MAPPING.md` and `ops/vps/services/cknexus-browser.cjs`.
- The local checkout had no usable `origin` remote (`git ls-remote origin` failed). Do not infer that its ahead commit is pushed or compare it to remote tracking refs until remote configuration is repaired.
- Do not reset, clean, checkout, overwrite, or remove those untracked files without a separate inspection and explicit work plan.

## 6. Required next actions — ordered, no duplicate work

1. **Reconcile subject identity first.** Inspect the subject-generation function and manifest/runbook for why the candidate workflows compute `eb0e…` while the release contract records `5129…`. Preserve the expected hash; produce an owner-reviewed correction or a new explicitly versioned candidate if the contract is wrong. Any source change invalidates downstream evidence for the old subject.
2. **Q10 remediation and review.** Triage the 22 Semgrep security ERROR findings, distinguish true positives from false positives with evidence, address actionable findings, rerun Q10 on the exact resulting candidate, then obtain independent security review and Owner approval. Do not suppress findings merely to obtain PASS.
3. **Q11 credential recovery.** Rotate/replace the rejected provider credential through the approved secret-management path; never print or commit it. Rerun live smoke on the exact reconciled candidate and require the sentinel.
4. **Q13 and Q15.** Execute PostgreSQL DR/restore and clean-host installation tests on the exact candidate; bind artifacts to the exact subject.
5. **Q14 and Q12 reconciliation.** Preserve the successful runtime evidence, then verify both against the authoritative subject after step 1.
6. **Q16 image remediation.** Inspect the 1 HIGH and 1 MEDIUM gate-level findings and the full image scan report; fix or formally review/approve per policy, then rebuild, rescan and bind image digest/provenance to the exact candidate. License inventory PASS alone is insufficient.
7. **AGNES/Observatory after release blockers are under control.** Inventory tracked/untracked/ignored files first; generate manifest metadata (`generated_at`, `source_sha`, `source_tree`, `is_stale`, `next_refresh_trigger`); then adopt indexers incrementally. Add work-resume conflict detection (branch owner, base SHA, handoff timestamp, dirty state, overlapping paths).
8. **Commercial readiness.** Reconcile #355 roadmap with a truthful product state; do not market CK-NEXUS as production-certified until all mandatory gates and independent approval are complete.

## 7. Non-negotiable operating rules

- NO EVIDENCE → NO DONE.
- Keep `DESIGNED → IMPLEMENTED → EXECUTED → VERIFIED → PRODUCTION` states distinct.
- SHA match is necessary but not sufficient; tests passing are not enough.
- CK-NEXUS Core / L3 owns state, memory, permissions, policy, execution and evidence. n8n is workflow plane only, not a release judge. External tools are not authorities.
- Never fabricate PASS, bypass a gate, expose secrets, self-approve, or promote a candidate based on another subject's evidence.
- Keep production release and development feature work separate. Final independent review and Owner release decision remain human-controlled.

## 8. Snapshot freshness

This file is a dated snapshot, not live telemetry. Refresh after every candidate commit, main update, PR state change, Q-gate run, runner/service change, or agent handoff. Each generated report/index must carry its own source SHA/tree and stale flag. If the observed source identity differs, mark derived evidence stale and reconcile before reuse.
