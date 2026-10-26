# CK-NEXUS GitHub Final Gate

## Purpose

The CK-NEXUS Final Gate is the last required quality/security gate before a change is merged into main. It runs for pull requests targeting main and for cknexus/auto-dev/** candidate branches. It uses read-only GitHub Actions permissions and does not commit, push, merge, deploy, or modify repository settings.

## Independent checks

- Quality: frozen dependency lock, compilation, and full Ruff checks.
- Security: reviewed Bandit findings and repository secret scan.
- Regression: portable pytest suite.
- Final gate: requires all three independent jobs to succeed and emits the exact candidate SHA.

Independent jobs ensure one failed lane does not hide evidence from the others. The final required check fails closed if any lane fails or is cancelled.

## Required repository configuration

A repository owner/admin must configure a GitHub ruleset or main branch protection with:

- Require a pull request before merging.
- Require status check: CK-NEXUS Final Gate / verify-before-merge.
- Require the existing CK-NEXUS CI / test status check as well.
- Require at least one approval and dismiss stale approvals after new commits.
- Require all review conversations to be resolved.
- Block force pushes and branch deletion.
- Do not allow routine bypass of required checks.

The status check must first be observed on a real pull request before selecting it in the ruleset. The current main branch has no classic branch protection and the existing ruleset only enables Copilot review plus deletion/non-fast-forward protections. Enable the required checks only after the workflow's baseline failures are resolved; never waive a failing security or quality result merely to merge the gate.

## Publication boundary

Auto GitOps may push a verified candidate to its isolated cknexus/auto-dev/** branch; that branch push triggers this workflow. This is candidate publication, not approval to update main. Merging into main must remain blocked until the required status checks and human review pass. This workflow intentionally has no write token or automatic-merge step.
