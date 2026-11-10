# Evidence Badge Automation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make Q10–Q16 badge generation deterministic, fail-closed, accessible, and safe to run from a trusted GitHub Actions workflow.

**Architecture:** The report generator consumes committed evidence only and emits deterministic Markdown/SVG artifacts. The automation workflow runs generator code from the protected main revision, writes only generated artifacts to the automation branch, separates write permissions by job, and creates a documentation PR whenever that branch is ahead of main.

**Tech Stack:** Python 3.13, unittest, Ruff, GitHub Actions, actionlint, yamllint, SVG.

**Spec:** Existing PR #364 scope and the Q10–Q16 evidence/authority contract.

## Global Constraints

- Preserve production_status = NO-GO; badge generation never changes release authority.
- Missing, invalid, stale, or mismatched evidence must never be upgraded to PASS or a numeric candidate.
- No force-push, history rewrite, or automatic merge.
- Only generated report/badge files may be automatically overwritten.
- Workflow write permissions must be job-scoped; untrusted branch code must not run with write credentials.
- The report must be deterministic for identical committed evidence.

## Review Focus

- Missing one of Q16's two required evidence files yields UNKNOWN with no percentage.
- Invalid UTF-8 or malformed evidence yields UNKNOWN rather than aborting generation.
- Any UNKNOWN member prevents a candidate aggregate from appearing as a numeric percentage.
- NOT_STARTED groups render 0%, not an average of unrelated member percentages.
- Runtime configuration changes invalidate evidence bound to older source subjects.
- A report does not change merely because a new commit was added.
- Every SVG status label has WCAG AA contrast for normal text.
- GitHub workflow conflict resolution is restricted to generated artifacts.
- Workflow PR creation recovers when the automation branch is already ahead but no PR exists.
- No self-hosted runner or privileged secret is introduced.

---

### Task 1: Evidence aggregation and deterministic report

**Files:**
- Modify: scripts/generate_update_report.py
- Test: tests/test_update_report_badges.py

- [x] Add failing tests for UNKNOWN aggregation, Q16 missing evidence, invalid UTF-8, NOT_STARTED group progress, runtime config staleness, and report determinism.
- [x] Run the focused tests and confirm the expected failures.
- [x] Implement fail-closed aggregation and Unicode decode handling.
- [x] Include runtime configuration in the evidence subject boundary.
- [x] Remove commit-history content from generated report output.
- [x] Run focused tests and Ruff.

### Task 2: Badge accessibility and documentation semantics

**Files:**
- Modify: scripts/render_badge.py
- Modify: README.md
- Test: tests/test_update_report_badges.py

- [x] Add failing contrast and README semantics tests.
- [x] Choose status colors with at least 4.5:1 contrast against white text.
- [x] Add descriptive badge alt text.
- [x] Explain conservative group status, arithmetic-mean index, and exact STALE conditions.
- [x] Run focused tests and Ruff.

### Task 3: Workflow trust and least privilege

**Files:**
- Modify: .github/workflows/auto-update.yml
- Test: tests/test_update_report_badges.py

- [x] Add failing static tests for trusted generator ordering, scoped permissions, separate concurrency, branch-ahead PR recovery, and safe conflict handling.
- [x] Generate report/badges from the protected main checkout before switching to the automation branch.
- [x] Resolve merge conflicts only when every conflict is one of the generated artifacts; fail on any source/workflow conflict.
- [x] Separate render, PR creation, verification, and PR-lint permissions.
- [x] Give lint and render independent concurrency groups.
- [x] Create or locate a PR whenever the automation branch is ahead of main, independent of whether the current run changed files.
- [x] Verify artifacts using trusted main scripts and compare them with the automation branch.
- [x] Run yamllint locally.
- [ ] Run actionlint in GitHub-hosted CI (no compatible Termux binary available).

### Task 4: Final verification and review response

- [x] Run 28 focused unit tests, compileall, Ruff, yamllint, YAML parse, and git diff --check.
- [ ] Confirm actionlint in GitHub-hosted CI.
- [ ] Inspect the complete diff and generated artifacts.
- [ ] Commit and push the branch; do not merge.
- [ ] Reply to and resolve only review threads whose findings are demonstrably addressed.
