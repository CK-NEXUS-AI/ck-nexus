# CK-NEXUS Read-only Reconciliation — 2026-10-15

## Scope and safety
Read-only verification of canonical GitHub refs, open PR check summaries, and selected Q10–Q12 host evidence. No workflow was triggered, no PR was merged, no source code was pushed, no deployment or service restart was performed, and no credential value was printed. This report is an audit snapshot, not a production certification.

## Canonical source identity
- Repository: `CK-NEXUS-AI/ck-nexus` (private)
- `main`: `cb612b72304246781b7dab48dad77d227c40d45d`
- `main` tree: `20f2073aae91a586619e91bbfd33cc93ab9da872`
- Audit branch before this report: `audit/20261014-readonly-baseline` at `00656ba6c093957ff0bbed19e882ef0005c56e81`
- Main remained unchanged during this audit.

## PR and CI snapshot
- PR #295 `fix: use GET for GitHub repository search API`, head `967cf8bc20bea01b4a7ba7d3fbfade21361f9ed1`, base current main. `harvest-and-gate`, `preflight`, `test`, and `attack-regression` all completed successfully. PR remains Draft/open. This is CI evidence for that PR head, not evidence of merge or production deployment.
- PR #294 `f8d13b0db2dd3e3b63ef08f58b1e4990c4924c80`: preflight, attack-regression, test passed; SonarCloud Code Analysis cancelled.
- PR #293 `b7bd83ba6d157dcfe353fa81744c75e7f14b4e13`: preflight, test, attack-regression passed; SonarCloud Code Analysis cancelled.
- PR #289 `e7e39ef063e4d6e5ab22649c891d7e7b0992562f`: integration, preflight, test, attack-regression passed; SonarCloud Code Analysis cancelled.
- PR #286 `1944c0b98af28b62166863152c544bc040ddcff9`: test failed; preflight and attack-regression passed; SonarCloud Code Analysis cancelled.
- A cancelled SonarCloud check does not establish the cause or a clean analysis. No SonarCloud configuration was changed.

## Q10 — Native security scan
- Existing `/opt/cknexus/evidence/automation/q10-status-20261007T042212Z.json` reports `status=NOT_VERIFIED`, `result=SCAN_FAILED`, `authentication_verified=false`, and historical source commit `b96049db9ae206bdc2292108629d8583ea0277d6`.
- Current CLI authentication status indicates login, but this does not substitute for a successful native Codex Security scan receipt bound to the current canonical source.
- No new native scan was started in this audit. Do not treat supplemental scanner results as a substitute for Q10.
- Gate: NOT_VERIFIED.

## Q11 — Provider/runtime
- Existing closeout evidence records production `NO-GO`; prior capability evidence reported authorization NOT_VERIFIED and live execution blocked by provider quota. Evidence is historical and bound to an older source identity.
- No provider call, credential change, or live execution was attempted in this audit.
- Gate: BLOCKED / NOT_VERIFIED pending owner-authorized credential/quota availability, authorization proof, and exact-source live evidence.

## Q12 — Runner sandbox enforcement
- Runner service was active with `Delegate=yes`, but `User`/`Group` were unset; `NoNewPrivileges=no`, `ProtectSystem=no`, `ProtectHome=no`, `PrivateTmp=no`, `RestrictSUIDSGID=no`, `LockPersonality=no`; capability bounding set included broad capabilities.
- `/sys/fs/cgroup/cknexus-delegated/cpu.max` = `max 100000`; `memory.max` = `max`; `pids.max` = `max`. Resource limits are not demonstrated by these values.
- OpenClaw health probe at `127.0.0.1:18789/health` returned HTTP `000`; no executable/process was verified. No wrapper was executed.
- Gate: NOT_VERIFIED. No service unit was modified or restarted.

## Q13–Q16 and release decision
- Previously inventoried Q13–Q16 evidence was not shown to be bound to the current canonical release identity. The current release-bound gate closure and final signed release artifact remain unverified.
- Overall production decision: **NO-GO**.

## Required next actions (blocked by evidence/authorization, not by plan)
1. Complete an authorized native Q10 scan on the exact canonical source and retain its native receipt; do not bypass provider quota.
2. Obtain owner-approved Q11 credential/quota and authorization, then produce live execution evidence bound to the same source identity.
3. Prepare a least-privilege Q12 runner hardening proposal, review it, and apply only with explicit change approval; then prove actual cgroup enforcement and isolated execution.
4. Reconcile Q13–Q16 artifacts to one canonical release identity and produce the final signed release artifact.
5. Resolve SonarCloud cancellation through authorized project/CI diagnostics; do not infer its cause.
6. Keep PR #295 Draft until human review/merge approval. Do not merge any PR solely because the checks listed here passed.

**Evidence state:** source/CI observations EXECUTED; the above gates are not VERIFIED for the current release. This report itself does not close any gate.
