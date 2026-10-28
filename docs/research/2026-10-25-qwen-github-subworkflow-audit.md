# Qwen Chat UI — GitHub Tool Sub-workflow Audit

Date: 2026-10-25
Target workflow: `Qwen Chat UI` (`y3NF4FlhVB5u9jWU`)
Source inspected: `backups/n8n-cloud/qwen-chat-ui-imported-20261024.json`
Target workflow active state: inactive in both the saved export and read-only workflow inventory.

## Findings (verified from the saved workflow export)

- The orchestrator has 10 directly attached tools: planner_agent, researcher_agent, coder_agent, reviewer_agent, merge_pull_request, comment_on_issue, run_server_command, list_open_issues, list_branches, delete_ai_branch.
- Nine GitHub HTTP/GitHub tool nodes are present in the workflow definition. Their configuration is not production-ready:
  - `create_branch` uses HTTP GET against `/git/refs`, although creating a ref requires POST.
  - `open_pull_request` uses GET against `/pulls`, although creating a PR requires POST.
  - `merge_pull_request` uses GET against `/pulls/{number}/merge`, although merging requires PUT.
  - GitHub HTTP Request nodes select `githubApi` as credential type but the exported nodes do not include credential references.
  - GitHub node credential references are explicitly marked `MISSING_ON_DESTINATION`.
- The n8n API key stored at `/root/.config/n8n/api_key` is used by the local CK-NEXUS workflow UI gateway. That gateway deliberately permits GET-only requests for workflows/executions and rejects mutations. It is an n8n management key, not proof of a GitHub API credential.
- The current API gateway reports six workflows. The Qwen Chat UI workflow is inactive. No workflow was activated or modified during this audit.

## Recommended decomposition

1. `repo_reader_tool`: read-only list/read operations; allow only repository `CK-NEXUS-AI/ck-nexus` by default; require explicit branch/ref.
2. `code_writer_tool`: create/update files only on `ai/*` branches. Resolve base ref SHA, create branch using POST, read existing file SHA for updates, use correct content encoding and commit message. Reject `main`/default branch writes.
3. `pr_manager_tool`: actions limited to `open`, `check`, `changes`, and `comment`. Merge must be a separate guarded operation requiring explicit human approval and verified review/check results; do not let an LLM's self-reported APPROVED string alone authorize merge.
4. Main orchestrator: planner_agent, researcher_agent, coder_agent, reviewer_agent, the three wrappers, and the server-command tool. Keep all workflows inactive until import and isolated tests pass.

## Credential reuse constraint

Reuse existing n8n credentials only if the destination instance actually has a GitHub credential with the required repository permissions. The exported workflow does not establish that: several references are missing and others are marked `MISSING_ON_DESTINATION`. Do not copy the Qwen credential or the n8n API management key into GitHub nodes, and do not paste any key into chat or execution data.

## Blocker and next safe action

The only available local workflow gateway is intentionally read-only; its upstream API key must not be repurposed to bypass that boundary. Consequently, live creation/import of the three workflows cannot be claimed from this environment. The next safe step is to configure/confirm an existing GitHub credential in the n8n UI, then import the sub-workflows into the inactive state and validate them with read-only tests before wiring the orchestrator. No merge or live GitHub write should be used as a dummy test.
