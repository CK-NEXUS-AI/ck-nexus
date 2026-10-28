# CK-NEXUS Execution Report — 2026-10-26

## Scope and preservation

- Repository: `/root/ck-nexus`; base HEAD: `bff3ef06b6e243226c36aafb03855125b5022311`.
- The primary working tree already contained extensive staged, unstaged, and untracked work. It was preserved; no reset, clean, stash, blanket staging, commit, merge, deployment, or credential change was performed.
- The report records a bounded execution pass, not a production-readiness declaration.

## Changes made in this pass

- Tightened the proactive maintenance task prompt to list the exact source paths accepted by the Auto Developer path policy. This addresses a previously observed task that changed `creator_app/ai_team/intelligence/smart_cache.py`, which the policy rejected.
- Added a regression test that proves the task prompt explicitly lists approved paths and excludes that rejected path.
- The regression test was first run and failed on the missing explicit path list, then passed after the implementation change.
- Prepared `docs/workflows/qwen-chat-ui-preactivation-safe-20261026.json` from the preserved export. The candidate is inactive, contains 27 nodes, has no imported credential references or dangling connections, corrects `create_branch` and `open_pull_request` to POST, and removes the merge, branch-deletion, and missing server-command tools. The live workflow was not changed or imported.

## Verification evidence

- Full repository test suite: **914 passed, 2 skipped, 1 warning in 62.68s**, exit 0.
- Focused automation regression suite after the final formatting-only adjustment: **51 passed in 6.62s**.
- Secret scan: **PASS**, 847 tracked files.
- Ruff check and format check for `creator_app/n8n_intelligence/proactive.py` and `tests/test_n8n_proactive.py`: **PASS**.
- `git diff --check`: **PASS**.
- A broader Ruff/format check over all changed Python files did not pass. It found existing style/format issues across multiple already-modified files, notably `ops/vps/services/cknexus_n8n_workflows_ui.py` and `scripts/api_key_setup.py`. Those files were not bulk-formatted because they contain existing user work and security-sensitive gateway code.

## Safe end-to-end canary

- Task: `cknexus-safe-canary-2026-10-26-01`.
- Task state: `completed`.
- Evidence: `/var/lib/cknexus/n8n-intelligence/auto-dev/cknexus-safe-canary-2026-10-26-01.json`.
- Agent exit code: 0; `tests_ok=true`; `head_unchanged=true`; `index_clean=true`; `safe_paths=true`; `changed_paths=[]`.
- Branch/worktree: `cknexus/auto-dev/f81359d0f6a8917f`, based on committed HEAD `bff3ef06b6e243226c36aafb03855125b5022311`.
- Auto GitOps correctly marked this no-change canary `gitops_state=skipped`, `gitops_reason=no_changes`. No empty branch was pushed.
- Important limitation: the isolated worktree starts from committed HEAD and does not automatically contain the primary checkout's uncommitted changes. The canary verifies the runner and verification path on the committed baseline, not the dirty primary working tree.

## GitOps publication evidence

An earlier verified task's branch publication was independently checked against the remote:

- Evidence file: `/var/lib/cknexus/n8n-intelligence/auto-dev/n8n-proactive-2026-10-24.attempt-2.json`.
- Branch: `cknexus/auto-dev/dc18b325364a804a`.
- Commit SHA: `4c5c091923e9e6b93f34fa47e1b52c9c5b7bbcf4`.
- Evidence says `gitops_state=published`, `gitops_reason=remote_sha_verified`, `push_verified=true`.
- A fresh read-only `git ls-remote` returned the same SHA for that exact branch.
- This publication belongs to the earlier proactive task, not the no-change canary in this report.

## Live operations snapshot

- n8n Intelligence latest observed run fetched 13 executions, with 0 new events and 0 tasks created; no actionable new event was found in that run.
- Task queue after the canary: 2 completed, 3 failed; no queued/running task was observed after completion.
- API Gateway, MCP, scanner, watchdog timer, n8n Intelligence timer, Auto Developer timer, Auto GitOps timer, and n8n Workflow UI Gateway were active at the latest check.
- Root filesystem: approximately 93% used, about 2.8 GB free. No data was deleted.
- `Qwen Chat UI` (`y3NF4FlhVB5u9jWU`) remains inactive. Prior live API evidence reports 30 nodes and `triggerCount=0` (no active triggers reported). No live workflow mutation was performed.

## Blockers and deferred work

1. **Qwen Chat UI is not ready for activation.** Destination Qwen/Alibaba and GitHub credentials are not confirmed; the referenced server-command sub-workflow is missing from the inspected destination inventory; `create_branch` and `open_pull_request` use GET where POST is required, and `merge_pull_request` uses GET where PUT is required.
2. **Credential setup requires the n8n editor.** The local CK-NEXUS workflow UI gateway is deliberately GET-only. Do not bypass it or repurpose the n8n management key as a provider/GitHub credential. Add/test credentials in n8n's Credentials UI without posting secrets into chat.
3. **No new actionable n8n events were available in the latest collector run.** The collector's read-only authentication worked, but the latest run produced no new tasks.
4. **Disk capacity remains constrained.** Do not remove `.hermes`, `.openclaw`, `.config`, `.local`, `.codex`, virtual environments, databases, backups, or browser profiles without a separate ownership/retention audit.
5. **Broad lint debt remains.** Review and repair the existing changed-file Ruff/format issues selectively; do not run a bulk formatter over the dirty working tree.
6. **No merge or production deployment is authorized by this run.** Keep `main` and production promotion behind explicit human approval.

## Next actions in priority order

1. Preserve the current working tree and diagnose the three failed task records from their sanitized evidence.
2. In n8n, configure and test Qwen/Alibaba and GitHub credentials; restore or remove the missing server-command sub-workflow.
3. Correct GitHub HTTP methods and run isolated read-only/manual tests while the workflow remains inactive.
4. Re-run the Auto Developer canary against an explicitly prepared candidate that includes the reviewed changes, without copying unrelated dirty files into a worktree.
5. Repair lint findings selectively and continue disk ownership/retention review.
6. Activate `Qwen Chat UI` only after credentials, dependencies, methods, and acceptance tests pass.
