# CK-NEXUS GitHub Final Gate

## Purpose

The CK-NEXUS Final Gate is the last required quality/security gate before a change is merged into main. It runs for pull requests targeting main and for cknexus/auto-dev/** candidate branches. It uses read-only GitHub Actions permissions and does not commit, push, merge, deploy, or modify repository settings.

## Checks

1. Reproducible dependency lock and environment sync.
2. Python compilation and Ruff.
3. Bandit findings against the repository's exact reviewed-finding allowlist.
4. Repository secret scan.
5. Portable regression test suite.
6. Emits the exact candidate commit SHA and PR identity in the job log.

## Required repository configuration

A repository owner/admin must configure a GitHub ruleset or main branch protection with:

- Require a pull request before merging.
- Require status check: CK-NEXUS Final Gate / verify-before-merge.
- Require the existing CK-NEXUS CI / test status check as well.
- Require at least one approval and dismiss stale approvals after new commits.
- Require all review conversations to be resolved.
- Block force pushes and branch deletion.
- Do not allow routine bypass of required checks.

The status check must first be observed on a real pull request before selecting it in the ruleset. The GitHub API connector in the current operator session returned 404 for repository metadata, so this workflow cannot truthfully claim that branch protection has been enabled. Configure and verify the ruleset using an authorized repository/org administrator.

## Publication boundary

Auto GitOps may push a verified candidate to its isolated cknexus/auto-dev/** branch; that branch push triggers this workflow. This is candidate publication, not approval to update main. Merging into main must remain blocked until the required status checks and human review pass. This workflow intentionally has no write token or automatic-merge step.
