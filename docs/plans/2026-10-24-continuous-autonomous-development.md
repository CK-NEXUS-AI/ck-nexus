# CK-NEXUS Continuous Autonomous Development Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run CK-NEXUS development tasks continuously in isolated worktrees, learn from structured outcomes, and publish only verified branches to GitHub.

**Architecture:** Existing n8n intelligence and task queue feed a bounded Auto Developer. Each eligible task gets a dedicated Git worktree and Codex sandbox. Tests and deterministic path policy produce evidence consumed by Agent Learning Memory and a separate Auto GitOps publisher.

**Tech Stack:** Python 3.12, pytest, Ruff, Git worktrees, Codex CLI, systemd timers, n8n, JSON evidence.

## Global Constraints

- Preserve all existing user changes; do not reset, stash, clean, or overwrite the primary checkout.
- Never stage with `git add -A`.
- No force-push, automatic merge to `main`, production deployment, credential rotation, or permission changes.
- Only allowlisted task handlers may reach the coding agent.
- Tests, diff checks, secret scanning, and remote SHA verification are required before publication.
- Learning context contains structured outcomes only, not prompts or raw assistant output.

---

### Task 1: Isolated Auto Developer workspaces

**Files:**
- Modify: `creator_app/n8n_intelligence/auto_developer.py`
- Modify: `ops/vps/scripts/cknexus_n8n_auto_developer.py`
- Modify: `ops/vps/systemd/cknexus-n8n-auto-developer.service`
- Test: `tests/test_n8n_auto_developer.py`

**Interfaces:**
- `AutoDeveloper(..., workspace_root=...)` creates `cknexus/auto-dev/<digest>` worktrees.
- Codex and pytest run with the task worktree as `cwd`; the primary checkout is read-only to the agent.

- [x] Verify dirty primary checkout remains unchanged while the task worktree is edited and tested.
- [x] Verify an ineligible task remains queued and does not invoke tools.

### Task 2: Evidence-only agent learning

**Files:**
- Create: `creator_app/n8n_intelligence/learning.py`
- Modify: `creator_app/n8n_intelligence/auto_developer.py`
- Test: `tests/test_n8n_agent_learning.py`

**Interfaces:**
- `AgentLearningMemory.context_for(task: str) -> str` returns bounded, sanitized outcome summaries.

- [x] Verify success/failure counts and repeated blocker codes.
- [x] Verify raw assistant output and secret-like values are never copied into learning context.

### Task 3: Verified GitOps publisher

**Files:**
- Create: `creator_app/n8n_intelligence/auto_gitops.py`
- Create: `ops/vps/scripts/cknexus_n8n_auto_gitops.py`
- Create: `ops/vps/systemd/cknexus-n8n-auto-gitops.service`
- Create: `ops/vps/systemd/cknexus-n8n-auto-gitops.timer`
- Test: `tests/test_n8n_auto_gitops.py`

**Interfaces:**
- `AutoGitOps.run_once() -> GitOpsRun` consumes verified evidence and publishes a single task branch.
- It stages only explicit allowlisted paths, scans staged diffs, pushes without force, and verifies the remote SHA.

- [x] Verify unsafe paths are blocked before Git mutation.
- [x] Verify a bare-remote integration test commits/pushes a task branch and leaves the primary checkout unchanged.

### Task 4: Operational activation and regression gate

**Files:**
- Install systemd units from `ops/vps/systemd/` into `/etc/systemd/system/`.
- Verify timers, logs, repository status, remote access, Ruff, and the full pytest suite.

- [x] Enable and observe the Auto GitOps timer.
- [ ] Confirm the configured remote can publish a task branch; if credentials or remote policy block it, record the failure without bypassing authentication.
- [ ] Preserve `main` and production deployment as human-reviewed promotion steps.

### Task 5: Daily proactive improvement cycle

**Files:**
- Modify: `creator_app/control_plane/task_store.py`
- Create: `creator_app/n8n_intelligence/proactive.py`
- Create: `ops/vps/scripts/cknexus_n8n_proactive.py`
- Create: `ops/vps/systemd/cknexus-n8n-proactive.service`
- Create: `ops/vps/systemd/cknexus-n8n-proactive.timer`
- Test: `tests/test_control_plane_task_store.py` and `tests/test_n8n_proactive.py`

**Interfaces:**
- `TaskStore.has_open_tasks() -> bool` returns whether queued or running work exists.
- `ProactiveTaskSeeder.run_once() -> ProactiveSeedResult` adds at most one fixed-scope, low-priority task per UTC day and never competes with queued/running work.

- [x] Verify queued/running task detection and duplicate-day prevention.
- [x] Verify seeded tasks retain `production_status=NO-GO` and `external_mutation_authorized=false`.
