# CK-NEXUS Continuous Autonomous Development — Design

## Goal

Keep CK-NEXUS improving through a bounded observe → diagnose → task → isolated development → verification → learning → GitHub publication loop without overwriting user work or allowing an agent to publish arbitrary changes.

## Current integration

```text
n8n execution signals + daily proactive seeder
  → Development Intelligence collector / bounded task queue
  → deduplicated evidence + Control Plane task queue
  → Auto Developer eligibility gate
  → dedicated Git worktree / Codex sandbox
  → tests + diff checks + path policy
  → evidence record
  → Agent Learning Memory (sanitized historical outcomes)
  → Auto GitOps path/secret/diff gate
  → commit + push to task branch
  → verify remote SHA
```

The existing `/root/ck-nexus` checkout is never used as an agent write target. Worktrees are based on the current committed `HEAD`; dirty user changes remain untouched. A task-specific branch is named `cknexus/auto-dev/<16-hex-digest>`.

## Agent Learning Memory

The next task receives a compact summary derived only from structured evidence: counts of verified/failed outcomes, repeated blocker codes, and paths from verified changes. It never replays task prompts, raw assistant output, secrets, or unrestricted log text. Learning is advisory; current repository evidence and current tests remain authoritative.

## Auto GitOps policy

- Only evidence marked `verified` with `tests_ok`, unchanged branch HEAD, clean index, and safe paths is eligible.
- Only narrowly allowlisted Python modules, tests, and Markdown docs may be published.
- Auto Developer, Auto GitOps, learning-memory, core queue, and policy-gate modules are protected from autonomous publication.
- Reject credential-like path names and common private-key/API-token patterns in the staged diff.
- Stage explicit evidence paths only; never use `git add -A`.
- Commit and push only to the task branch; verify the exact remote SHA.
- Never force-push, merge into `main`, deploy to production, or change credentials/permissions.
- Remote divergence, tests failing, secret patterns, changed path mismatch, or invalid evidence stops publication and records a reason.
- A published worktree is removed only after the remote SHA is verified; the remote branch remains available for review.

## Scheduling

- n8n intelligence collection: every two minutes (existing timer).
- Auto Developer: every two minutes (existing timer, now uses isolated worktrees).
- Auto GitOps: every five minutes.
- Proactive maintenance seeder: once per day, only when the task queue has no queued/running work; one deterministic task ID per UTC day prevents duplicates.

## Success criteria

1. A dirty primary checkout does not block or get modified by an eligible agent task.
2. Unsafe tasks remain unclaimed; failed verification cannot reach GitOps.
3. Learning context is bounded and excludes raw model output.
4. GitOps rejects forbidden paths and secrets before commit.
5. A local bare-remote integration test proves branch commit, push, and remote-SHA verification without modifying the primary checkout.
6. Production deployment and main-branch merge remain outside this automation's authority.
