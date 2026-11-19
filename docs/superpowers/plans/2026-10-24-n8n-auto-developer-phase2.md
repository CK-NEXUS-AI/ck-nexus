# n8n Auto Developer Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically process eligible n8n development tasks through a bounded local coding agent and verification gate without automatic Git release operations.

**Architecture:** Add a queue peek operation, a safe auto-developer policy/executor, a short-lived CLI/systemd worker, and evidence storage. The runner only claims typed n8n tasks, refuses unsafe repository states, invokes an installed coding assistant with workspace-write sandboxing, verifies the resulting work, and never commits or pushes.

**Tech Stack:** Python 3.12 stdlib, SQLite, systemd, Codex CLI, pytest, Ruff.

**Spec:** `docs/specs/2026-10-24-n8n-auto-developer-phase2-design.md`

## Global Constraints

- Preserve all existing user changes.
- Never use `git add -A`.
- Never commit, push, force-push, merge, deploy, or change branches.
- Only `n8n_development_signal` tasks are eligible.
- One active run at a time.
- Do not run when the repository has unsafe/unreviewed existing changes.
- Never expose secrets to the coding assistant or logs.
- Keep production status `NO-GO`.

## Review Focus

- Dirty repository with existing changes must remain queued rather than being overwritten.
- Malicious command-like task descriptions must remain data and never become shell commands.
- Coding-agent failure must preserve source changes and record evidence.
- Successful tests must not imply Git release authority.
- Concurrent timer invocations must not run two developers simultaneously.

### Task 1: Queue inspection and safe auto-developer contracts

**Files:**
- Modify: `creator_app/control_plane/task_store.py`
- Create: `creator_app/n8n_intelligence/auto_developer.py`
- Test: `tests/test_n8n_auto_developer.py`

- [ ] Add failing tests for queue peek, handler/policy validation, dirty-repo blocking, command-like input rejection, and evidence contract.
- [ ] Run targeted tests RED.
- [ ] Implement `peek_next()` and deterministic `AutoDeveloperPolicy`.
- [ ] Run targeted tests GREEN and Ruff.

### Task 2: Bounded coding-agent executor

**Files:**
- Modify: `creator_app/n8n_intelligence/auto_developer.py`
- Test: `tests/test_n8n_auto_developer.py`

- [ ] Add failing tests for runner command construction, timeout/failure handling, and post-run Git safety checks.
- [ ] Run RED.
- [ ] Implement injected subprocess runner; default to Codex CLI with `--sandbox workspace-write`, no Git operations, bounded timeout, and sanitized environment.
- [ ] Run GREEN and Ruff.

### Task 3: Worker CLI and systemd automation

**Files:**
- Create: `ops/vps/scripts/cknexus_n8n_auto_developer.py`
- Create: `ops/vps/systemd/cknexus-n8n-auto-developer.service`
- Create: `ops/vps/systemd/cknexus-n8n-auto-developer.timer`
- Test: `tests/test_n8n_auto_developer_cli.py`

- [ ] Add failing CLI tests for idle, blocked, successful, and failed cycles.
- [ ] Run RED.
- [ ] Implement one-cycle worker with lock and bounded timeout.
- [ ] Add hardened systemd unit/timer at 2-minute interval.
- [ ] Run GREEN, Ruff, and `git diff --check`.

### Task 4: Production activation and evidence

- [ ] Validate systemd units.
- [ ] Enable timer.
- [ ] Run one manual cycle without claiming source mutation success if the repository is currently unsafe.
- [ ] Verify queue remains safe, evidence is written outside the repo, and no Git commit/push occurs.
- [ ] Run targeted tests and existing Fast/n8n intelligence tests.
- [ ] Run `git diff --check`.
