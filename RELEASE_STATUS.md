> **Evidence subject:** Q10 scanner PASS เฉพาะ commit `22edd1f` (run 41231931695).
> Q11–Q16 ยัง NOT_VERIFIED บน main ปัจจุบัน `f4c4447` และต้องรันใหม่.

# Release Status — CK-NEXUS Q10-Q16 Closure

Decision: **NO-GO FOR PRODUCTION CLAIMS**

Canonical main: 22edd1f07147f7223cf02abba056c6ce4a3beee0 (verified current main; tree 3a742e8b91001efb3558fc2cdb9a617fbc4e6c9a)
Closure branch: release/q10-q16-closure (historical evidence line; not rebased to current main)
Previous closure head: a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53 (historical)
Previous frozen runtime/security source SHA: ad2fac7aa0752117dde065c7ad9b0b8d41136aa2 (superseded for current main)
Previous frozen source tree: eb2074176319072ca3f31d5c8c990752ba849b0a (superseded for current main)
Previous frozen runtime/deployment subject: 772662ac4ed60e785f30370c0c66bfdf8f798ea5f67fe13063404b20f2f74200 (superseded for current main)
Unified application subject: `dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec`
Closure contract: `docs/Q10_Q16_CLOSURE_CONTRACT.md`

## Current main rebaseline status — 2026-10-31

Live repository verification found current canonical main 22edd1f07147f7223cf02abba056c6ce4a3beee0, tree 3a742e8b91001efb3558fc2cdb9a617fbc4e6c9a. Recomputing the runbook runtime/deployment path set on current main yields c8e6dca69fd241e6f555ae9ccd880cdd3b34c8d7b2417c94b3ca89dce9b95ef9, not the previous frozen subject 772662ac... . PR #330 added services/email_gateway/attachments.py to the runtime path set and changed the subject. The old Q11–Q16 evidence remains historical only and is not evidence for current main.

- Current-subject Q10 layered scanner: PASS on source 22edd1f07147f7223cf02abba056c6ce4a3beee0, tree 3a742e8b91001efb3558fc2cdb9a617fbc4e6c9a, runtime subject c8e6dca69fd241e6f555ae9ccd880cdd3b34c8d7b2417c94b3ca89dce9b95ef9; workflow run 41231931695; report SHA-256 db33d3e7b80f34b13f42a235aea5e59f6efc470b92550cd7297804b492692389; 0 dependency vulnerabilities, 0 Bandit high, 0 Bandit medium, secret scan exit 0, attack regression exit 0. 513 Bandit low findings remain visible for disposition.
- Q10 whole gate: NOT_VERIFIED until an independent human reviews the exact report/findings and attests.
- Q11 current-subject: NOT_VERIFIED / BLOCKED. Existing workflow remains pinned to the previous subject; secret-name presence does not prove a successful exact-subject provider run.
- Q12 current-subject: NOT_VERIFIED / BLOCKED. Registered cknexus-q12 GitHub runner is offline; no current-subject delegated cgroup evidence exists.
- Q13, Q14, Q15 and Q16 evidence currently recorded below is bound to the previous subject and is STALE FOR CURRENT MAIN until each gate is rerun against the new exact subject.
- Production remains NO-GO. No Q10–Q16 promotion or owner approval is implied by the Q10 scanner PASS.

Issue #329 was updated with this exact mismatch and the evidence blockers. Workflow constants and previous subject-bound evidence were deliberately not rewritten because Q11–Q16 evidence has not yet been regenerated.

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
| Q10 dependency component | **PASS (current main scanner)** | run 41231931695; 0 dependency vulnerabilities; report SHA-256 db33d3e7... |
| Q10 whole security gate | **NOT_VERIFIED / BLOCKER** | Current main scanner PASS on 22edd1f (run 41231931695, report sha256 db33d3e7...); independent human review/disposition still required |
| Q11 live provider P0-AI-001 | **NOT_VERIFIED / BLOCKED** | Existing evidence is previous-subject only; workflow remains pinned to ad2fac7a; no current-subject run |
| Q12 delegated cgroup v2 | **NOT_VERIFIED / BLOCKED** | Current cknexus-q12 runner is registered but OFFLINE; no current-subject delegated cgroup v2 evidence |
| Q13 PostgreSQL DR | **NOT_VERIFIED / STALE SUBJECT** | Previous run 31950497105 is historical; rerun required on current subject |
| Q14 observability/operator delivery | **NOT_VERIFIED / STALE SUBJECT** | Previous run 31950773095 is historical; rerun required on current subject |
| Q15 clean-machine deployment | **NOT_VERIFIED / STALE SUBJECT** | Previous run 31950497105 is historical; rerun required on current subject |
| Q16 production image | **NOT_VERIFIED / STALE SUBJECT** | Previous run 31950497111 is historical; rerun required on current subject |
| Q16 runtime license inventory | **NOT_VERIFIED / STALE SUBJECT** | Previous run 31950497135 is historical; rerun required on current subject |
| Q16 final merge/tag/package | **NOT ELIGIBLE** | blocked by Q10 whole gate + Q11 + Q12 |

## Previous Q10 authority (historical; current request is not rebaselined)

Previous canonical request: `evidence/q10/Q10_SCAN_REQUEST_FINAL_SUBJECT.json`

Required scan identity:

- target SHA: `ad2fac7aa0752117dde065c7ad9b0b8d41136aa2`
- target tree: `eb2074176319072ca3f31d5c8c990752ba849b0a`
- release subject: `772662ac4ed60e785f30370c0c66bfdf8f798ea5f67fe13063404b20f2f74200`
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
