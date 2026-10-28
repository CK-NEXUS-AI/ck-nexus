# CK-NEXUS Autonomous Completion Plan

> **For agentic workers:** Execute tasks in order using the current host's remote terminal and repository tools. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the highest-impact CK-NEXUS development-automation gaps, prove the n8n-to-queue-to-development-to-evidence flow, and publish only explicitly verified task branches without losing existing work.

**Architecture:** Keep the primary checkout and its uncommitted changes intact. First establish a trustworthy baseline and make Auto Developer failures diagnosable; then fix queue/workspace/policy defects using isolated tests and worktrees. Finally run bounded end-to-end canaries, verify evidence and GitOps publication, and leave any action requiring external authorization or unavailable credentials explicitly blocked.

**Tech Stack:** Python 3.12, pytest, Git, Codex CLI, SQLite, n8n API, systemd timers, JSON evidence, GitHub remote.

## Global Constraints

- Preserve every existing user change; never run `git reset`, `git clean`, `git stash`, blanket staging, or destructive cleanup.
- The primary checkout `/root/ck-nexus` is dirty; do not overwrite or discard its modifications or untracked files.
- Never stage with `git add -A`; stage only exact reviewed paths.
- Do not print, copy into evidence, or expose credentials, raw provider output, or secrets.
- Do not force-push, merge into `main`, deploy to production, rotate credentials, or change access permissions.
- Only allowlisted task handlers and paths may reach the coding agent.
- A task is not complete without reproducible test output, diff/security checks, and sanitized evidence tied to the exact source revision.
- `production_status` remains `NO-GO` and `external_mutation_authorized=false` for automation tasks.
- Never delete Docker images, volumes, worktrees, backups, or other data merely to free disk space.
- Current VPS disk capacity is a constraint; prefer targeted tests and bounded logs over full reinstallations.

---

### Task 1: Establish baseline and preserve the primary checkout

**Files:**
- Inspect: `/root/ck-nexus` Git state and existing plan/spec/test files.
- Create: `docs/plans/2026-10-26-autonomous-completion-plan.md` (this file).
- Test: existing focused n8n intelligence, Auto Developer, Auto GitOps, proactive, and task-store tests.

**Interfaces:**
- Consumes: current working tree, service/timer status, SQLite queue, and prior evidence.
- Produces: a recorded baseline and a bounded list of verified blockers; no destructive repository mutation.

- [x] Record branch, upstream relation, modified/untracked paths, service/timer state, queue counts, and disk capacity.
- [x] Run focused regression tests and retain the exact exit code/summary: 42 passed, exit 0.
- [x] Confirm edits are narrowly scoped; preserve the original working-tree changes.

### Task 2: Make Auto Developer failures diagnosable without leaking secrets

**Files:**
- Modify: `creator_app/n8n_intelligence/auto_developer.py`
- Test: `tests/test_n8n_auto_developer.py`

**Interfaces:**
- `AutoDeveloper.run_once() -> DevelopmentRun` continues to return bounded state/reason/evidence.
- Evidence records a redacted, single-line diagnostic for non-zero Codex exits, but never raw model output or secret-like values.

- [x] Add tests proving non-zero assistant exits retain a useful redacted diagnostic and do not mark the task verified.
- [x] Verify the new tests fail against current behavior.
- [x] Fix the failure-path diagnostic selection and redact API keys and Authorization Bearer values from the single-line diagnostic.
- [x] Run focused tests and `git diff --check`; targeted tests pass.

### Task 3: Repair the queue-to-workspace execution contract

**Files:**
- Modify: `creator_app/n8n_intelligence/auto_developer.py`, `creator_app/n8n_intelligence/analysis.py`.
- Test: `tests/test_n8n_auto_developer.py`, `tests/test_n8n_intelligence_analysis.py`, `tests/test_n8n_intelligence_cli.py`, and the focused queue/collector/GitOps test modules.

**Interfaces:**
- The collector creates an idempotent task only for a new, actionable event.
- The developer executes only an approved handler/payload in an isolated, clean worktree; denied paths or invalid task contracts remain unverified.
- Failed tasks are retried only within the existing bounded retry policy and never in an unbounded loop.
- Retry reuses only a registered, matching, clean worktree; dirty or mismatched worktrees remain untouched and are rejected.

- [x] Add regression tests for Authorization Bearer redaction, failure diagnostics, explicit edit-scope prompting, and safe worktree reuse.
- [x] Verify each new regression test fails before changing implementation.
- [x] Implement the smallest fixes justified by the tests; preserve secret/path/sandbox policy and reject dirty worktrees.
- [x] Run focused queue, collector, developer, GitOps, analysis, and task-store tests: 42 passed; Ruff and `git diff --check` passed.

### Task 4: Verify end-to-end automation and publish only verified work

**Files:**
- Inspect/modify only as needed: `creator_app/n8n_intelligence/auto_gitops.py`, `scripts/n8n_evidence_export.py`, `scripts/secret_scan.py`, relevant systemd units, and their tests.
- Evidence: `/var/lib/cknexus/n8n-intelligence/auto-dev/` and a new timestamped sanitized verification record outside the tracked source tree.

**Interfaces:**
- n8n telemetry -> deduplicated intelligence event -> eligible queue item -> bounded Auto Developer -> tests/security checks -> sanitized evidence -> Auto GitOps branch publication.
- No merge to `main`, production deployment, force-push, or automatic credential/access changes.

- [x] Verify n8n authentication and read-only collection without printing the API key.
- [x] Run one bounded canary with a known safe task and confirm queue state, worktree, exit code, tests, changed paths, and evidence all agree.
- [x] Verify the GitOps publisher accepts only matching verified evidence and only allowlisted paths; if remote auth/policy blocks publication, record the blocker and do not bypass it.
- [x] Run the relevant regression suite and secret scan; run the full suite only if disk/RAM headroom permits.
- [x] Report completed, blocked, and deferred work separately, with command outputs and evidence paths.

## Execution update — 2026-10-26

See `docs/reports/2026-10-26-ck-nexus-execution-report.md` for exact evidence and remaining blockers. Current run verified read-only n8n collection, a bounded Auto Developer canary, focused and full tests, secret scan, and a previously published GitOps branch SHA. The no-change canary was correctly skipped by GitOps. Qwen Chat UI remains inactive pending credentials, the missing sub-workflow, and HTTP method fixes. The primary checkout remains dirty and preserved.

## Observed blockers at plan creation

- Root filesystem is approximately 93% used with about 2.8 GB free; no bulk cleanup is authorized by this plan.
- The primary checkout is on `main`, synchronized with its upstream commit, but contains numerous modified and untracked files that must be preserved.
- The intelligence collector fetched 13 executions, but the latest runs found no new actionable events; the task queue contained four failed tasks and no queued/running tasks.
- Prior Auto Developer evidence shows multiple `verification_failed` results. One failed quickly with Codex exit code 2 and no useful diagnostic in evidence; another changed paths rejected by the current path policy.
- The worktree runner creates branches from committed `HEAD`, so existing uncommitted primary-checkout changes are not automatically included in its task workspaces. Do not assume those workspaces contain the latest in-progress implementation.
- Auto GitOps reports `no_verified_work_pending`; no successful publication is established by the current evidence.

## Completion criteria

- Focused regression tests pass for the repaired failure/queue/workspace behavior.
- The primary checkout's pre-existing changes remain present and are not silently staged, committed, discarded, or overwritten.
- At least one bounded, safe end-to-end canary reaches verified local evidence; publication is claimed only if a remote branch SHA is actually confirmed.
- All remaining blockers are listed with exact evidence; no production-readiness claim is made without its separate approval gates.
