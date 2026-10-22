# CK-NEXUS Verification Pipeline Hardening

Date: 2026-10-22
Repository: `/root/ck-nexus`
Scope: harden the existing ControlPlaneVerifier and verify repository/runtime status. No LLM inference, paid API call, service restart, deployment, commit, or unrelated-file cleanup was performed.

## Changes

File: `creator_app/control_plane/verification.py`

1. `evaluate()` now denies VERIFIED/release evidence if the evidence-reference list is empty or any reference is blank/whitespace.
2. `repair_loop()` applies the same evidence gate before running any verification callback.
3. Exceptions from the verification callback no longer escape the bounded loop. Each exception counts as an unsuccessful attempt; the loop continues only within `max_repairs + 1` attempts, and then fails closed.
4. A verifier exception is never interpreted as success. `patch_applied` remains false: this component is a verification/retry gate, not an automatic source-code patcher.

Regression tests added in `tests/test_control_plane_verification.py`:
- empty/blank evidence is rejected by evaluate;
- verification callback exceptions are bounded and return FAILED;
- a successful callback cannot release work without evidence.

## TDD evidence

- Red run before implementation: 3 new tests failed for the intended behavior gaps (empty evidence accepted, callback exception escaped, and repair loop accepted empty evidence).
- Green run after implementation: `6 passed in 0.10s` for the focused verification tests.
- Related Control Plane tests: `21 passed in 2.10s`.
- Full repository test suite: `756 passed, 2 skipped, 1 warning in 43.95s`.
- Changed-file Ruff: passed.
- Changed-file Python compile check: passed.
- `git diff --check`: passed for tracked diff; the changed verifier/test files are currently untracked in this worktree, so that command alone does not validate their content.

## Repository-wide verification findings

- Repository-wide Ruff `ruff check .` failed with **196 findings** across the current worktree, including long-line findings in existing/untracked files such as `tests/test_omni_provider.py`. These were not auto-fixed because the worktree contains many pre-existing modifications and untracked work; broad autofix could alter unrelated work.
- Live `scripts/ck-health` returned exit 0 with overall `WARN`, not PASS:
  - systemd is `degraded` due to `fwupd-refresh.service`;
  - root filesystem is 90.2% used (3.82 GiB free; warning threshold 85%);
  - Git worktree has 68 dirty entries and branch drift `ahead 6, behind 1`;
  - the OpenClaw CLI is absent from the VPS PATH.
  - Required CK-NEXUS services were active, required Docker containers were running, MCP port 8765 was loopback-only, and MCP protocol initialize returned HTTP 200.
- The health script wrote its normal timestamped evidence directory under `evidence/2026-10-21/phase-1/` according to the VPS clock. It did not restart services or mutate source code.

## Limitations / honest status

The verifier is more robust for evidence gating and transient verification failures, but no system can be guaranteed to work 100% across all inputs, host failures, dependencies, and runtime conditions. The full suite passes, while repository-wide Ruff and live health still have known WARN/FAIL findings. This change does not automatically edit or repair arbitrary source code; it makes verification retries bounded and release decisions fail closed. Actual code repair requires a separately authorized patch executor, safe diff review, and the same test/security pipeline afterward.

## Next priority

1. Triage the 196 Ruff findings by ownership and changed-file status; do not run blanket autofix.
2. Investigate `fwupd-refresh.service` failure and disk pressure without deleting runtime data.
3. Review Git divergence/dirty worktree before any merge/rebase; preserve all current changes.
4. Add explicit machine-readable pipeline summary and repair/verification evidence links before enabling automated source patching.
