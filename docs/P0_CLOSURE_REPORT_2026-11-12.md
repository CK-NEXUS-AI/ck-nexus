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

## 8. Fail-closed containment update — 2026-11-13

The follow-up source review confirmed that the production Worker path passed
`output["approver_token"]` directly to `TaskStore.finish(success=True)`.
The TaskStore and AuthorityStore are independently configured SQLite stores
(`CKNEXUS_TASK_DB` and `CKNEXUS_COUNCIL_AUTHORITY_DB`); no evidence established
that they share a database file or transaction boundary. The Worker also wrote
a `completed` checkpoint before attempting the authoritative task transition.

A containment patch was applied in the current worktree:

- `TaskStore.finish(success=True)` now rejects completion, even when a valid
  Admin identity token is supplied. It validates the live worker lease first
  and rolls back without changing task state or result.
- Failure transitions use an explicit `BEGIN IMMEDIATE` transaction and retain
  lease fencing.
- `RepairWorker` no longer forwards handler-provided approver tokens and no
  longer writes a `completed` checkpoint before the task transition.
- Regression tests now assert that an Admin identity token alone cannot
  complete a task. Worker verification without an L3 grant fails closed.
- The MCP error now states that a task-bound Core/L3 completion grant is
  required; an Admin identity token alone is insufficient.

**Disposition remains NOT P0-CLOSED.** This is a containment measure, not the
final L3 integration. Successful queue completion is intentionally unavailable
until a Core/L3-issued grant is bound to the task, operation, execution/lease,
worker and evidence digest, and grant consumption plus task completion are
proven atomic in one authoritative transaction. No synthetic grant issuer or
worker-held signing secret was introduced.

Validation on the current Termux worktree (2026-11-13):

- Focused P0/task/worker/proactive tests:
  `34 passed, 1 warning` (11.04s).
- Connector gate/fabric tests:
  `11 passed, 1 warning` (6.50s).
- Capability Authority and n8n AutoDeveloper tests:
  `22 passed, 1 warning` (4.92s).
- `compileall` for control_plane, council_authority and connector_fabric: PASS.
- `git diff --check`: PASS.
- Ruff: NOT RUN; Ruff is not installed in this Termux environment.
- MCP runtime tests: BLOCKED at collection because `anyio` is not installed
  (`ModuleNotFoundError: No module named 'anyio'`).
- The pytest warning is an unknown `asyncio_mode` option because the
  pytest-asyncio plugin is not installed.

These tests prove the containment behavior, not the missing positive L3
completion-grant path. No CI, independent review, merge, deployment or
production claim is implied.

## 9. Post-push CI annotations and automated review findings

### Exact GitHub runner failure

For the post-push CodeQL runs on commit `25b907606c25a5a60f3455161ea12c7410902628`, check-run annotations for Python, JavaScript/TypeScript, and Actions all returned the exact failure:

`The job was not started because your account is locked due to a billing issue.`

The jobs had empty step lists and failed-job logs were unavailable (`log not found`). Therefore these are external runner-start blockers, not CodeQL source-analysis findings. No CI check is considered PASS.

### Cubic AI review

The latest available Cubic review reported **14 findings across 13 files**, but its review-post marker binds it to the prior PR head `2d99a3a92d42cd8c48e21dff06c2b1cdb92bff5c`, not the current pushed head. Re-review on the current SHA is required. Findings to revalidate include:

- P0: TaskStore completion approval/evidence is not bound to `job_id`; cross-task token/evidence reuse remains a valid unresolved risk until task-bound Core/L3 capability enforcement is integrated.
- P1: `scripts/fast_swarm_result.json` claims test results not produced by `fast_swarm.py`; AutoDeveloper approval fallback marks work failed without a resume path; `fast_swarm.py` assumes an untracked `.venv_fast`.
- P2/P3: test environment variables leak across tests; missing separate valid-token/no-evidence regression; raw null identity claims can be coerced to the string `None`; worker tests lose success-path assertions; patch scripts do not verify replacement counts/postconditions; test generation is not idempotent; MCP evidence/token fields need size checks; import ordering issue.

These are AI-generated review findings, not independent human review. They have not been marked resolved by this report. Each must be validated against the current PR head, fixed or rebutted with evidence, and independently reviewed where required.

## Continued remediation — 2026-11-12

Workspace: `fix/p0-authorization-bypass-20261112`
Base HEAD before this remediation: `df47c411a465b1c07846358f8a9b7b196e147935`

Implemented in the current uncommitted worktree:
- Capability grant consumption now checks the persisted grant task binding.
- Task-scoped evidence quality now rejects evidence whose task_id is null or belongs to another task.
- Identity verification validates raw service_id, agent_id, and role claims as non-empty strings before constructing CallerIdentity.
- Test identity secrets are isolated per test through monkeypatch fixtures in the affected test modules.
- Agnes execute requests accept a caller-supplied execution_id and pass it into the execution plan so approval retries can reuse the original execution identity.
- MCP task completion bounds evidence_reference (2,048 chars) and approver_token (4,096 chars), and checks the serialized result after evidence_reference augmentation.

Validation on the current worktree:
- Command: `.venv_fast/bin/python -m pytest -q tests/test_council_capability_authority.py tests/p0_repro_test.py tests/test_control_plane_task_store.py tests/test_control_plane_worker.py tests/test_n8n_proactive.py tests/test_n8n_auto_developer.py`
- Result: **54 passed, 1 warning** in 12.76s (measured test runtime; remote process runtime 19.83s).
- Warning: pytest reports the configured `asyncio_mode` option is unknown in this environment.
- Ruff check on the changed implementation and test files: **PASS** (`All checks passed!`).
- `git diff --check`: **PASS**.
- Combined collection attempt including MCP and Agnes execution-kernel modules: **BLOCKED** with two collection errors: MCP requires missing `anyio`; Agnes execution-kernel tests require missing `fastapi`. Neither dependency was installed.
- The passing 54-test run therefore excludes both blocked modules; their tests are NOT PASS.

Still NOT CLOSED:
- P0: The fail-closed containment update now rejects general admin identity tokens in `TaskStore.finish()`, but successful completion is not yet integrated with a task- and evidence-bound Core/L3 CapabilityAuthority grant. The positive grant-consumption path and atomic completion transaction remain open.
- P1: AutoDeveloper still marks approval-required tasks failed rather than providing a durable approval-resume state.
- P1: fast_swarm report generation and clean-checkout interpreter discovery remain unresolved.
- P1: public Agnes approval retry needs end-to-end API/runtime tests proving the original execution_id and correlation_id survive the approval round-trip.
- MCP handler behavior and bounded completion changes remain unverified by runtime tests because `anyio` is unavailable.
- GitHub Actions billing lock still prevents hosted runners from starting; those checks are EXTERNAL BLOCKED, not PASS.
- No merge, deployment, production promotion or independent-review claim was made. The containment patch is eligible for a feature-branch commit, but does not close P0.
