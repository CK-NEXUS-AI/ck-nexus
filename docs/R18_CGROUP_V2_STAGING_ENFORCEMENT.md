# CK-NEXUS R18 — cgroup v2 Staging Enforcement

Decision: **DEVELOPMENT CANDIDATE / PRODUCTION NO-GO**

R17 baseline: `dec0f1bd86c7d4d39433fb76345aa9086954e7e8`

## Increment

- Adds an explicit `CKNEXUS_AGNES_CGROUP_ROOT` for a delegated cgroup v2 subtree.
- Requires `cpu`, `memory`, and `pids` controllers plus a writable delegated root.
- Phase 3 staging/production initialization fails closed when cgroup enforcement is unavailable.
- Development remains usable but truthfully reports the hardened runner as not production-safe.
- Adds a staging-only enforcement gate that creates a probe cgroup, applies CPU/memory/PID limits,
  attaches a disposable child process, verifies the effective controller files, and cleans up.
- The gate refuses to run unless `CKNEXUS_ENVIRONMENT=staging`.

## Current-host evidence

The current host exposes unified cgroup v2 and the required controllers, but `/sys/fs/cgroup` is not
writable/delegated. Therefore live staging enforcement is **BLOCKED**, not PASS. No probe cgroup is
created when the health preflight fails.

## Verification

- R18/R17/Phase 3 targeted tests: 17/17 PASS.
- Non-billing regression: 181/181 PASS.
- Full suite: 187 PASS / 3 ERROR; all errors are the pre-existing missing `aiosqlite` dependency.
- Python compile: PASS.
- Ruff/Bandit/pip-audit: BLOCKED because those modules are not provisioned in this host.
- No production deployment or external service mutation was performed.
