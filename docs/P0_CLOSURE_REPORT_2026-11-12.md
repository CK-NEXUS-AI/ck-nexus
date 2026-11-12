# CK-NEXUS P0 / PR #369 — Closure Evidence and Disclosure

**Report date:** 2026-11-12 (Asia/Bangkok)
**Repository:** `CK-NEXUS-AI/ck-nexus`
**Branch:** `fix/p0-authorization-bypass-20261112`
**Pre-report HEAD:** `2d99a3a92d42cd8c48e21dff06c2b1cdb92bff5c`
**PR:** [#369](https://github.com/CK-NEXUS-AI/ck-nexus/pull/369)
**Disposition:** **RC WITH DISCLOSURE — NOT P0-CLOSED; NOT PRODUCTION-READY**

## 1. Work completed and directly evidenced

### Approval cache replay remediation

- `creator_app/agnes/execution/approval.py`: sticky approval fingerprint now includes `execution_id` and `correlation_id`.
- `tests/test_agnes_execution_kernel_phase1.py`: added `test_sticky_approval_fingerprint_is_bound_to_execution_id`.
- Direct runtime regression reproduction on the current worktree: two requests differing by execution/correlation IDs produce different fingerprints; the approval for execution 1 is accepted for execution 1 and rejected for execution 2.
- Result: `PASS: approval fingerprint is execution-bound; cross-execution replay denied`.

### Local validation

- Focused P0 regression suite: **37 passed, 1 warning** (5.28s).
- Ruff on the two changed Python files: **PASS** (`All checks passed!`).
- `git diff --check`: **PASS**.

## 2. Tests not executed / blocked

- Direct pytest collection of `tests/test_agnes_execution_kernel_phase1.py` is **BLOCKED** because `fastapi` is not installed in either available virtual environment. The collection error is `ModuleNotFoundError: No module named 'fastapi'`.
- MCP runtime tests are **NOT RUN** because `anyio` is unavailable.
- No dependencies were installed as part of this work.
- These results are not represented as PASS.

## 3. Authorization findings still open

### A-0 — Capability Authority integration: PARTIAL / OPEN

The current `TaskStore.finish()` completion path does not yet demonstrate mandatory enforcement of the Core/L3 capability grant, task-bound authorization, and artifact-backed evidence verification. Existing `CapabilityAuthority` code and grant-consumption paths do not by themselves prove that every completion path is protected.

Required closure: enforce the authoritative grant on the actual completion path; bind it to task ID, parameters, evidence digest and provenance; atomically consume it once; fail closed on missing, mismatched, expired, or reused grants; prove the Worker/MCP paths cannot bypass Core/L3.

### A-1 — Signing-key custody: STRUCTURAL RISK / OPEN

Prior source inspection found the identity verifier exposes both token issue and verify functionality around a shared HMAC secret. A verifier process that possesses the shared signing secret can also mint tokens. No secret values were read and no claim is made about production secret distribution.

Required closure: Core/L3 alone holds the private signing key; Worker/MCP receive verification-only public keys; grants are task/parameter/evidence-bound, expiring, nonce-bearing, and atomically one-time consumed. Select the asymmetric implementation only after validating existing dependency support.

### Other open authorization items

- `/api/agnes/approvals` accepts `approved_by` from request input; authoritative identity binding has not yet been proven.
- Full task/evidence binding and cross-task evidence rejection are not yet verified.
- The cache replay patch closes only the identified `StickyApprovalResolver` cross-execution reuse case; it does not close TaskStore grant replay or the broader A-0/A-1 trust-boundary findings.

## 4. GitHub PR / CI state at inspection

- PR #369: **OPEN**.
- `mergeStateStatus`: **BLOCKED**.
- `reviewDecision`: **REVIEW_REQUIRED**.
- Head SHA at inspection: `2d99a3a92d42cd8c48e21dff06c2b1cdb92bff5c`.
- The required GitHub checks failed before runner execution. The affected jobs had empty step lists; the reported account-level cause is a billing lock (`The job was not started because your account is locked due to a billing issue.`).
- This is classified as **EXTERNAL BLOCKED**, not a code test failure and not a passing CI result.
- No merge, approval, deployment, billing change, or production promotion was performed.

## 5. Independent review and release decision

- Cubic AI review is automated assistance, not an independent human security review.
- Independent human security review remains **PENDING**.
- This report supports a transparent Release Candidate handoff with disclosure only. It does **not** certify P0 closure, security approval, or Production Readiness.

## 6. Remaining closure requirements

1. Complete A-0 integration and task/evidence binding in the real TaskStore completion path.
2. Complete A-1 asymmetric key custody and verification-only Worker/MCP design.
3. Bind `/api/agnes/approvals` to authoritative human identity.
4. Run the direct Agnes regression file in an environment with the repository's declared FastAPI test dependencies; run MCP runtime tests in the supported environment with `anyio` available. Do not silently omit either suite.
5. Resolve GitHub billing lock through the authorized account owner, then rerun all required PR workflows.
6. Resolve all P0/P1 review findings and obtain independent human security review.
7. Recompute evidence against the final exact commit SHA and obtain Owner release decision before any merge/deploy/production claim.

## 7. Evidence integrity

This report deliberately distinguishes executed tests, blocked tests, source-inspection findings, and external blockers. A test not run is not PASS. A CI job that never started is not PASS. A code patch or report is not proof that the remaining authorization paths are secure.
