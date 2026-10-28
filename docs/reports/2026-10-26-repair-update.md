# CK-NEXUS Repair Update — 2026-10-26

## Verified repository identity
- VPS: `vps3680569.trouble-free.net`
- Repository: `/root/ck-nexus`
- Branch HEAD: `bff3ef06b6e243226c36aafb03855125b5022311`
- `origin/main`: `bff3ef06b6e243226c36aafb03855125b5022311`
- Working tree remains dirty with 50 status entries. No existing changes were discarded; no commit or push was made.

## Root cause found and repaired
`AutoDeveloper._create_workspace()` reused a clean task worktree without checking whether its HEAD matched the current repository HEAD. Live evidence showed two failed-task worktrees based on `013cb0770d6138d2500fae8ca6e70aa367a261d4`, while current repository HEAD was `bff3ef06b6e243226c36aafb03855125b5022311`.

The workspace creator now:
1. Reads the current repository HEAD.
2. Reuses a registered, clean worktree only when its HEAD matches.
3. Preserves an existing stale worktree and creates a separate worktree/branch keyed to the current HEAD.
4. Verifies the new worktree HEAD before returning it.
5. Refuses to reuse or overwrite dirty or identity-mismatched worktrees.

A test was observed failing before the fix because the stale workspace was reused, then passed after the fix. The two historical Codex exit-code-2 tasks have no captured diagnostic text, so the stale-worktree bug is a confirmed defect but is **not proven to be the sole cause** of those Codex exits.

## Verification
- Focused tests: **52 passed** across 7 test groups.
- Ruff: passed for `auto_developer.py` and `test_n8n_auto_developer.py`.
- `git diff --check`: passed.
- Python bytecode compilation for changed Python files: passed.
- Secret scan: **PASS, 847 tracked files**.
- Codex CLI smoke diagnostic: `codex-cli 0.162.1`, sanitized environment, harmless no-tool prompt, exit code 0 and response `READY`. This proves the current CLI can start; it does not retrospectively identify the cause of prior failures.
- Full repository suite was not run in this round.
- Four existing auto-development worktrees remain present; stale worktrees were preserved rather than deleted or reset.

## Remaining blockers
- Failed task records: `n8n-proactive-2026-10-25`, `n8n-db881c9fc66eb6e5a601`, and `n8n-4e14d0195747a42028a1`. Current task-store data shows **one attempt recorded per task**, not three. The two n8n execution tasks contain only workflow/execution IDs and lack diagnostic output; do not blindly retry until execution details are retrieved.
- Qwen Chat UI live workflow remains unactivated. The local pre-activation candidate has 27 nodes, no attached credential IDs, `create_branch=POST`, `open_pull_request=POST`, and intentionally no merge tool. Destination credentials and live-workflow/subworkflow validation still need to be completed before activation.
- Remote MCP remains loopback-only at `127.0.0.1:8765`; no authenticated public HTTPS endpoint was configured.
- Windows device `WIN-DV9R14TH0N5` did not respond to the read-only remote diagnostic call during this round. Its WinRM/RDP/firewall state therefore remains unverified; no Windows settings were changed.
- No commit, push, workflow activation, public port exposure, or production mutation occurred.


## Follow-up repair — 2026-10-26
- Confirmed the focused suite after the follow-up changes: **53 passed in 7.14s** across the same 7 test groups.
- AutoDeveloper-specific tests: **9 passed**.
- Ruff: passed for `creator_app/n8n_intelligence/auto_developer.py` and `tests/test_n8n_auto_developer.py`.
- Secret scan: `SECRET SCAN: PASS (847 tracked files)`.
- `git diff --check`: passed.
- Added redacted test diagnostics to auto-development evidence: pytest exit code, one sanitized failure line, and diff-check exit code. This closes the previous observability gap where a task could be marked `verification_failed` without recording why its test phase failed.
- Added bounded fallback worktree paths (up to four retry suffixes) so repeated failed attempts can use a fresh worktree while preserving earlier dirty worktrees. Added regression coverage proving both prior dirty worktrees are preserved and a third clean worktree is created.
- Safely requeued only `n8n-proactive-2026-10-25` after confirming the queue was empty, the task was NO-GO / external-mutation-disabled, and its retry budget allowed one final attempt. The worker claimed attempt 3; the run is still in progress at the time of this update. No other failed tasks were requeued.
- The n8n task records now confirm `n8n-db881c9fc66eb6e5a601` and `n8n-4e14d0195747a42028a1` remain failed with one attempt each and lack execution diagnostic details. They remain untouched.
- Current source changes are still uncommitted; no push, workflow activation, production deployment, or external MCP exposure was performed.
