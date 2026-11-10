# Q10 Native Codex Scan Retirement — Owner Decision Record

**Decision date:** 2026-11-05 (Asia/Bangkok)

**Decision:** `OWNER_APPROVED_PENDING_INDEPENDENT_SECURITY_REVIEW`
**Scope:** CK-NEXUS Q10 for the current release-closure line only.

## Owner decision

The repository Owner explicitly requested that Q10 be closed without using Codex and approved the end-to-end Q10–Q16 closure plan on 2026-11-05. This records the Owner's direction to retire the native Codex Security Deep Scan requirement for this closure line and to evaluate the open-source layered gate defined in `Q10_OPEN_SOURCE_GATE_PROPOSAL.md`.

This is **not** a claim that open-source tools are equivalent to Codex Security. It is a change in the accepted evidence method, not a claim of equal detection coverage. The previous native-scan requirement and historical evidence are preserved as history; no old evidence is rewritten.

## Replacement evidence contract

The proposed replacement requires all of the following on one immutable candidate subject:

1. Semgrep static analysis with pinned version and ruleset.
2. Bandit Python security scan.
3. Gitleaks repository-history and tracked-file scan with secret redaction.
4. `pip-audit` against the frozen environment.
5. Trivy filesystem and configuration scan.
6. CK-NEXUS security attack regression suite.
7. Coverage/completeness checks, raw report hashes, tool versions, exit codes, source SHA/tree, and release-subject manifest hash.

Critical/high findings, exposed credentials, dependency vulnerabilities, authorization/evidence-forgery regressions, and failed negative tests block the gate. Medium findings require a documented reviewer decision. Low/informational findings remain visible and require review; they are not silently suppressed.

## Remaining mandatory approval

- An independent authorized security reviewer must assess non-equivalence, coverage, tool configuration, findings, false-positive handling, and the final exact-subject evidence.
- The reviewer must be a person other than the repository Owner and must attest using their own identity. Automation and the Owner cannot create that attestation on the reviewer's behalf.
- After independent review, the Owner must record the final Q10 approval against the exact candidate source SHA, tree SHA, release subject, report SHA-256, and workflow run ID.

The immutable scanner evidence is never rewritten to manufacture a PASS. Its `gate_result` remains `NOT_VERIFIED` and `production_promotion_allowed` remains `false`, including after human review. The release provenance verifier independently checks the actual GitHub PR review, reviewer repository association, pinned Owner account and approval comment, timing, exact candidate SHA/tree, runtime subject, and report SHA-256. Only that verified attestation can establish an **effective Q10 PASS in the final release manifest**. The original scanner evidence remains unchanged.

Until those attestations are verified:

- `Q10_DEPENDENCY_AUDIT.json.gate_result` remains `NOT_VERIFIED`;
- `security_review_status` remains `REQUIRED`;
- `independent_review_status` remains `PENDING`;
- `owner_approval_status` remains `PENDING` for the final gate decision;
- `production_promotion_allowed` remains `false`;
- the release remains `NO-GO`.

## Integrity

This decision record does not modify historical Q10 evidence, does not authorize production deployment, and does not permit a workflow or script to manufacture reviewer identity or a Q10 `PASS` result.
