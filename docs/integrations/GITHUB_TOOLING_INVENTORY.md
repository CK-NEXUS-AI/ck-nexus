# GitHub Organization Tool Inventory and Auto-Use Protocol

- Target organization/repository: CK-NEXUS-AI / ck-nexus
- Recorded from the tools exposed to this ChatGPT session on 2026-10-21.
- Available GitHub connector tools discovered: 89
- This is an inventory of tools exposed to the current session, not a claim that every organization/repository is accessible. Permissions and API access are checked at call time.
- Automatic-use protocol for CK-NEXUS tasks:
  1. Use GitHub tools first for repository metadata, files, branches, commits, issues, pull requests, reviews, and CI evidence when access succeeds.
  2. If GitHub API returns 404/permission errors, do not assume the repository is absent. Report the access limitation and use the authorized VPS Git remote only as a fallback for local work.
  3. Before code changes, inspect repository instructions, branch/commit relationship, working-tree status, and existing diffs.
  4. Preserve uncommitted and untracked work. Never reset, force-push, merge, delete, publish, or rerun workflows with side effects unless explicitly authorized.
  5. Verify outputs from tests/CI and report actual results, not expected results.
  6. Tool availability is session-scoped; re-discover tools if the connector set changes.
- Important limitation: this file documents invocation guidance; it cannot itself activate tools or guarantee automatic invocation in a future chat where the connector is unavailable.

## Available GitHub tools

- `mcp__GitHub__add_comment_to_issue`
- `mcp__GitHub__add_issue_assignees`
- `mcp__GitHub__add_issue_labels`
- `mcp__GitHub__add_reaction_to_issue_comment`
- `mcp__GitHub__add_reaction_to_pr`
- `mcp__GitHub__add_reaction_to_pr_review_comment`
- `mcp__GitHub__add_review_to_pr`
- `mcp__GitHub__compare_commits`
- `mcp__GitHub__convert_pull_request_to_draft`
- `mcp__GitHub__create_blob`
- `mcp__GitHub__create_branch`
- `mcp__GitHub__create_commit`
- `mcp__GitHub__create_file`
- `mcp__GitHub__create_issue`
- `mcp__GitHub__create_pull_request`
- `mcp__GitHub__create_tree`
- `mcp__GitHub__delete_file`
- `mcp__GitHub__dismiss_pull_request_review`
- `mcp__GitHub__download_user_content`
- `mcp__GitHub__download_workflow_artifact`
- `mcp__GitHub__enable_auto_merge`
- `mcp__GitHub__fetch`
- `mcp__GitHub__fetch_blob`
- `mcp__GitHub__fetch_commit`
- `mcp__GitHub__fetch_commit_workflow_runs`
- `mcp__GitHub__fetch_file`
- `mcp__GitHub__fetch_issue`
- `mcp__GitHub__fetch_issue_comments`
- `mcp__GitHub__fetch_pr`
- `mcp__GitHub__fetch_pr_comments`
- `mcp__GitHub__fetch_pr_file_patch`
- `mcp__GitHub__fetch_pr_patch`
- `mcp__GitHub__fetch_workflow_job_logs`
- `mcp__GitHub__fetch_workflow_job_steps`
- `mcp__GitHub__fetch_workflow_run_artifacts`
- `mcp__GitHub__fetch_workflow_run_jobs`
- `mcp__GitHub__get_commit_combined_status`
- `mcp__GitHub__get_issue_comment_reactions`
- `mcp__GitHub__get_pr_diff`
- `mcp__GitHub__get_pr_info`
- `mcp__GitHub__get_pr_reactions`
- `mcp__GitHub__get_pr_review_comment_reactions`
- `mcp__GitHub__get_profile`
- `mcp__GitHub__get_repo`
- `mcp__GitHub__get_repo_collaborator_permission`
- `mcp__GitHub__get_user_login`
- `mcp__GitHub__get_users_recent_prs_in_repo`
- `mcp__GitHub__label_pr`
- `mcp__GitHub__list_installations`
- `mcp__GitHub__list_installed_accounts`
- `mcp__GitHub__list_pr_changed_filenames`
- `mcp__GitHub__list_pull_request_review_threads`
- `mcp__GitHub__list_pull_request_reviews`
- `mcp__GitHub__list_recent_issues`
- `mcp__GitHub__list_repositories`
- `mcp__GitHub__list_repositories_by_affiliation`
- `mcp__GitHub__list_repositories_by_installation`
- `mcp__GitHub__list_user_org_memberships`
- `mcp__GitHub__list_user_orgs`
- `mcp__GitHub__lock_issue_conversation`
- `mcp__GitHub__mark_pull_request_ready_for_review`
- `mcp__GitHub__merge_pull_request`
- `mcp__GitHub__remove_issue_assignees`
- `mcp__GitHub__remove_issue_label`
- `mcp__GitHub__remove_pull_request_reviewers`
- `mcp__GitHub__remove_reaction_from_issue_comment`
- `mcp__GitHub__remove_reaction_from_pr`
- `mcp__GitHub__remove_reaction_from_pr_review_comment`
- `mcp__GitHub__reply_to_review_comment`
- `mcp__GitHub__request_pull_request_reviewers`
- `mcp__GitHub__rerun_failed_workflow_run_jobs`
- `mcp__GitHub__rerun_workflow_job`
- `mcp__GitHub__resolve_review_thread`
- `mcp__GitHub__search`
- `mcp__GitHub__search_branches`
- `mcp__GitHub__search_commits`
- `mcp__GitHub__search_installed_repositories_streaming`
- `mcp__GitHub__search_installed_repositories_v2`
- `mcp__GitHub__search_issues`
- `mcp__GitHub__search_prs`
- `mcp__GitHub__search_repositories`
- `mcp__GitHub__unlock_issue_conversation`
- `mcp__GitHub__unresolve_review_thread`
- `mcp__GitHub__update_file`
- `mcp__GitHub__update_issue`
- `mcp__GitHub__update_issue_comment`
- `mcp__GitHub__update_pull_request`
- `mcp__GitHub__update_ref`
- `mcp__GitHub__update_review_comment`
