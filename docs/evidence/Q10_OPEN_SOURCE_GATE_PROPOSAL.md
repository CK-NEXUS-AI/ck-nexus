# Q10 Open-Source Security Gate — Owner-Approved Alternative Pending Review

**Status:** `OWNER_APPROVED_PENDING_INDEPENDENT_SECURITY_REVIEW`
**Authority:** Owner direction recorded in `Q10_NATIVE_SCAN_RETIREMENT_DECISION.md` on 2026-11-05; the canonical Q10 result remains `NOT_VERIFIED` until independent review and final Owner approval.
**Cost constraint:** designed to run with free, locally runnable/open-source tools and GitHub Actions; it must not require paid model/API credits.

## 1. Purpose and non-equivalence

This proposal defines the Owner-approved direction for a reproducible, auditable alternative to the native Codex Security Deep Scan requirement, pending independent review and canonical contract adoption. It is **not** a claim that open-source scanners are equivalent to Codex Security.

The Owner has approved the direction to retire the native Codex scan requirement for this closure line. The alternative is not yet fully adopted because independent security review is still required. Existing Q10 evidence must stay `NOT_VERIFIED`; no script, workflow, PR, or test may silently convert that state to `PASS`.

## 2. Required subject binding

Every run must record and verify all of the following before scanning:

- Full Git commit SHA and Git tree SHA of the exact candidate subject.
- Canonical release-subject manifest SHA-256 and the manifest contents used for the run.
- Scanner workflow commit SHA, tool versions, configuration digests, and execution environment identity.
- Start/end timestamps, per-tool exit codes, raw output paths, and SHA-256 for every output.
- A machine-readable summary linking each finding to the exact subject, path, rule, severity, and disposition.

A mismatch, missing field, unpinned tool/configuration, partial run, unavailable scanner, or unverifiable artifact must fail closed as `NOT_VERIFIED` (or `BLOCKED` where execution did not occur). A report from another commit/tree is not transferable evidence.

## 3. Minimum free-tool evidence set

Run each applicable tool on the same immutable subject and retain raw outputs:

1. **Semgrep** — CLI `1.183.0` with `semgrep/semgrep-rules` pinned to commit `16b9e6d45f10649f6a531ec4838ed9924372c3bc` (Python, JavaScript, TypeScript, generic, Dockerfile, YAML, Bash, and JSON rule directories); record complete findings.
2. **Bandit** — Python security findings with a versioned, reviewed disposition for every medium/high finding. Never use a moving or undocumented allowlist.
3. **Gitleaks** — tracked-file and repository-history secret scan as configured; any potential credential must be investigated. Never publish secret values in logs or reports.
4. **pip-audit** (or another explicitly approved, pinned dependency auditor) — dependency inventory, vulnerability identifiers, and fix/disposition status.
5. **Trivy** — applicable filesystem/configuration/image scans; record which targets were and were not scanned.
6. **CK-NEXUS security regression suite** — deterministic negative tests for authorization boundaries, prompt/data isolation, unsafe tool invocation, secret redaction, evidence provenance, and fail-closed behavior.
7. **Coverage and completeness checks** — prove the expected files/targets were scanned and all required outputs exist. A zero-finding report without coverage/completeness evidence is insufficient.

Tool failures are not passes. A scanner that is unavailable or cannot execute must be reported as `BLOCKED`; it must not be omitted silently. A tool may be substituted only through a reviewed, versioned contract change.

## 4. Finding disposition

- Any confirmed exposed credential, critical/high exploitable issue, authorization bypass, evidence-forgery path, or regression failure blocks the gate.
- Medium findings require a documented risk decision by the authorized reviewer, linked to a fix or a time-bounded exception; they are not automatically waived.
- Low/informational findings must remain visible in the report. Suppressions require a narrow rule/path/line scope, reason, owner, expiry/review date, and tests that prevent the suppression from masking unrelated findings.
- False positives require evidence and independent review; do not edit scanner output or weaken a detector merely to obtain a green check.

## 5. Independent review and decision states

The scanner workflow produces evidence, not approval. The final report must use explicit states:

- `BLOCKED`: required execution could not run or a prerequisite is missing.
- `NOT_VERIFIED`: evidence is incomplete, mismatched, or not independently validated.
- `READY_FOR_HUMAN_REVIEW`: required scans completed and evidence integrity/completeness checks passed, but review is pending.
- `REJECTED`: a blocking finding or failed acceptance criterion remains.
- `PASS`: only after the contract has been formally adopted, the exact-subject evidence is complete, an independent authorized reviewer attests to the results, and the Owner approves the release decision.

The automation must never generate an Owner attestation or independent-review identity on another person's behalf.

## 6. Required adoption sequence

1. Review this proposal and the candidate workflow/code in a dedicated PR.
2. Compare coverage, false-positive handling, threat model, and failure modes against the existing native-scan contract; document known gaps and non-equivalence.
3. Record the Owner decision (completed; see `Q10_NATIVE_SCAN_RETIREMENT_DECISION.md`).
4. Obtain independent security review of the proposed non-equivalent replacement and its implementation.
5. Update the canonical Q10 contract and its tests in a reviewed change; retain the previous contract and its evidence history.
6. Run the new gate against the exact final release subject and verify commit/tree/manifest binding and artifact hashes.
7. Obtain independent human attestation and final Owner sign-off before any production promotion decision.

Until all seven steps complete, the canonical Q10 result remains `NOT_VERIFIED` and production remains `NO-GO`.

## 7. Explicit exclusions

This proposal does not:

- change or rewrite the frozen Q10 subject or its evidence;
- declare the existing Q10 native scan complete;
- convert Q10 `NOT_VERIFIED` to `PASS`;
- establish Q11 live-provider readiness or substitute offline mocks for live-provider evidence;
- authorize merging unrelated draft PRs, deploying to production, or changing runtime credentials;
- require paid API keys, paid scanner subscriptions, or remote compute.

## 8. Acceptance checklist for this proposal PR

- [ ] Security reviewer confirms the proposal does not silently redefine the current Q10 result.
- [ ] Maintainer confirms proposed tools are pinned and runnable in the intended free CI/runtime environment.
- [ ] Threat-model and coverage comparison against the current contract is documented.
- [x] Owner approved the non-Codex direction on 2026-11-05; see the decision record.
- [ ] Independent security reviewer approves the non-equivalent replacement and implementation.
- [ ] Exact-subject evidence, independent review, and Owner sign-off are completed before production promotion.
