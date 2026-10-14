# CK-NEXUS Read-only Baseline Audit

- Captured at (UTC): 2026-10-14T21:09:24Z
- Repository: https://github.com/CK-NEXUS-AI/ck-nexus
- Branch inspected: main
- Base commit inspected: `cb612b72304246781b7dab48dad77d227c40d45d`
- Base tree inspected: `20f2073aae91a586619e91bbfd33cc93ab9da872`
- GitHub commit signature verification: `true` (reason: `valid`)
- Method: read-only GitHub API/CLI inspection and read-only VPS health/process checks.
- Change boundary: this report is being added on a separate audit branch; main is not modified, no PR merged, no workflow executed, and no service/configuration changed.

## Canonical repository and release identity

- Live GitHub metadata confirms the private repository `CK-NEXUS-AI/ck-nexus`, default branch `main`, not archived.
- The current main commit observed during capture is `cb612b72304246781b7dab48dad77d227c40d45d` with tree `20f2073aae91a586619e91bbfd33cc93ab9da872`; GitHub reports the commit signature as verified/valid.
- This supersedes older remembered SHA values for current-main identification. Historical evidence must remain attached to the commit/tree it originally inspected.

## GitHub merge policy and CI observations

- Active ruleset observed: ID `24928564`, name `Copilot review for default branch`, enforcement `active`.
- Rules in that ruleset: `deletion`, `non_fast_forward`, and `copilot_code_review` (`review_on_push=false`, `review_draft_pull_requests=true`). No required PR-review rule or required status-check rule appeared in the returned ruleset detail.
- Classic branch protection API for `main` returned HTTP 404 with message `Branch not protected` at capture time. The active ruleset remains in effect; do not interpret this as no governance at all.
- Combined commit status endpoint returned `pending` with zero legacy status entries.
- Check-runs endpoint returned 20 entries in the first page. The returned entries included multiple completed `harvest-and-gate` failures (latest observed completion 2026-10-14T17:34:07Z) and completed `preflight` successes (latest observed completion 2026-10-14T17:09:15Z), plus other historical check runs. These results are not proof of required-check enforcement.
- Open PR inventory at capture included PR #295 (draft), #294 (draft), #293 (open non-draft), #292 (draft), #291 (draft), #290 (draft), #289 (open non-draft), and #287 (draft), among others. No PR was merged or changed by this audit.
- Historical evidence from the VPS audit dated 2026-10-13 also documented that PR check rollups and commit check-runs differed for PRs #295 and #287 because manual `workflow_dispatch` runs produced `harvest-and-gate` checks. Treat that as historical context and re-check before changing rules.

## VPS observations

- Captured health HTTP status: n8n on `127.0.0.1:5678/health` = 200; scanner on `127.0.0.1:8787/health` = 200; API gateway on `127.0.0.1:8790/health` = 200; OpenClaw candidate on `127.0.0.1:18789/health` = 000.
- Current service inventory identified `cknexus-api-gateway.service` active/running, `cknexus-scanner.service` active/running, and the Q12 GitHub Actions Runner service active/running.
- A previous check queried `cknexus-gateway.service` and found it inactive; the actual service name is `cknexus-api-gateway.service`. This naming discrepancy is resolved by the current service inventory, but API health alone does not prove production readiness.
- Listener inspection showed the above ports bound to loopback. The process on port 8790 was reported as `python3`; this does not alone prove its security posture.
- `/opt/cknexus` exists but is not a Git worktree in the current check. Do not use it as the canonical source checkout.
- No OpenClaw listener was present on port 18789 in this capture. OpenClaw runtime remains NOT VERIFIED.

## Gate status / limitations

- Q10 security, Q11 live execution, Q12 sandbox enforcement, and Q13-Q16 release-bound evidence were not fully re-run by this capture. Historical evidence has blockers and must not be upgraded to PASS from this report.
- Production status remains NO-GO until all required gates have fresh evidence bound to one canonical release identity.
- This is an unsigned audit summary, not a release attestation, vulnerability clearance, or production certification.

## Next actions

1. Verify Q10 Native Codex Security availability and scan the canonical release-bound source.
2. Re-test Q11 secure credential injection/provider authorization without exposing credentials.
3. Prove Q12 kernel-level resource enforcement and sandbox boundaries with controlled negative tests.
4. Reconcile Q13-Q16 evidence to the exact release identity and run E2E/recovery verification.
5. Propose merge-protection changes only after the required reviewer and deterministic CI contexts are confirmed; do not lock merges on unstable check names.
6. Re-check OpenClaw provenance and runtime installation before any launch or install action.

## Evidence interpretation rules

- Executed != verified; CI pass != deployed; HTTP 200 != production-ready; file exists != service running; hash match != verified.
- No finding is marked PASS unless direct evidence supports that exact gate and source identity.
