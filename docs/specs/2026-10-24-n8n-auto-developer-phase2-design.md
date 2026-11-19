# CK-NEXUS — n8n Auto Developer Phase 2 Design

**Date:** 2026-10-24
**Status:** Authorized for implementation by explicit user instruction to start
**Goal:** Turn safe n8n development tasks into bounded automatic development runs with verification evidence, without allowing the automation to commit or push Git changes.

## Architecture

```text
n8n Intelligence Queue
        |
        v
Auto Developer Gate
  | task contract
  | repository safety
  | allowed paths / secret denylist
  | single active run
        |
        v
Codex CLI (or approved local coding assistant)
  sandbox=workspace-write
  approval=automatic
        |
        v
Tests / diff validation
        |
        v
Evidence + task result
        |
        v
Separate Auto-GitOps gate
```

## Safety

- Only `handler=n8n_development_signal` tasks are eligible.
- `production_status` must remain `NO-GO` and `external_mutation_authorized=false`.
- No automatic `git commit`, `git push`, branch changes, force push, or deployment.
- Never run when the repository has unrelated pre-existing changes that cannot be preserved safely.
- Never modify secret/config files such as `.env*`, credentials, keys, certificates, or runtime state.
- One development run at a time; bounded timeout.
- Coding assistant receives sanitized task data only.
- Evidence is stored outside the tracked repository.
- A successful development run means verified local work/evidence, not release approval.

## Eligibility

Default `AUTO_SAFE` policy:

1. Task handler is exactly `n8n_development_signal`.
2. Priority is 2 or 3.
3. Repository is in a safe state for automated editing.
4. Coding assistant is installed and available.
5. Required test command is available.
6. No denied path is in the agent's requested scope.

If the repository is dirty, the developer does not claim the task and leaves it queued for a later safe cycle.

## Execution

The runner uses `codex exec` with `--sandbox workspace-write` and automatic approval. The prompt explicitly forbids Git mutations and secret access. The runner captures the final response and performs deterministic post-run checks.

## Verification

At minimum:

- `git diff --check`
- targeted tests when task metadata identifies them; otherwise the repository's bounded default test command
- no staged changes
- no commit/push performed by the runner
- evidence JSON with start/end, task ID, assistant, exit code, test result, and changed paths

## Failure handling

Failures leave the source changes intact for inspection, record evidence, and do not release or push anything. The task is marked failed after the bounded worker attempt; normal queue retry policy applies.

## Non-goals

- No automatic GitHub push.
- No force push.
- No production deployment.
- No arbitrary shell commands supplied by n8n or an LLM.
- No secrets passed to the coding assistant.
