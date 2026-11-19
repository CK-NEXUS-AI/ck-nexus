# AGNES Execution Kernel Phase 1 — Validation

Baseline parent: `4f864ea00d51ce8029629d58ae4f16b8f39257b0` (R13 AGNES Skill Nervous System).

Posture: **Development Candidate / LAB / NO-GO**. This is local development evidence, not R12 production evidence.

## Results

- Phase-1 security targeted tests: **20 PASS**
- R13 AGNES + Phase-1 tests: **33 PASS**
- R9-R11 canonical tests: **23 PASS**
- Non-billing regression: **151 PASS**
- Full suite: **157 PASS / 3 ERROR**
- Full-suite errors are the existing billing environment blocker: `ModuleNotFoundError: aiosqlite`
- Python compileall: **PASS**
- Tracked secret scan after staging: **PASS (237 tracked files)**
- Internal SHA256 manifest: **236 entries** (SHA256SUMS excludes itself)
- `git diff --check`: **PASS**
- Ruff: **BLOCKED** in this sandbox (`No module named ruff`)
- Bandit: **BLOCKED** in this sandbox (`No module named bandit`)

## Security coverage proved locally

1. Requests are deeply frozen at construction.
2. Immutable execution manifest hashes are stable.
3. Sticky approval changes when inputs change.
4. Sticky approval changes when permission grants or credential requirements change.
5. Missing executor fails closed; there is no host-shell fallback.
6. Pre-audit occurs before executor invocation.
7. A pre-audit outage blocks before executor invocation.
8. Final evidence/audit is emitted for completed execution.
9. Global/tenant/executor/skill kill-switch hierarchy is implemented; skill-level behavior is directly tested.
10. Skill/executor manifest mismatch is blocked.
11. Executable skills require explicit capability grants.
12. HIGH/CRITICAL paths require sticky approval.
13. HIGH/CRITICAL paths are blocked while idempotency is only in-memory/non-durable.
14. Production mutation remains denied.
15. Executor risk escalation cannot reuse a lower-risk manifest/approval scope.
16. User-sourced credential leases are rejected.
17. Reusing one idempotency key with a different manifest is rejected.
18. Result verification rejects execution/skill identity mismatch.
19. Artifact promotion cannot jump directly from candidate to promoted.
20. Status/API explicitly report `Agent != Executor`, `Workspace != Sandbox`, and sandbox executor disabled.

## Deliberate Phase-1 blockers

- No LocalSandboxExecutor is registered.
- No Docker/E2B/Daytona/Codespaces live executor is registered.
- No durable PostgreSQL/Redis idempotency backend is connected to this kernel yet.
- No auto-merge.
- No auto-production deployment.
- No production self-modification.

R12 staging evidence remains mandatory before any production-ready claim.
