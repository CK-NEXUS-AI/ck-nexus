---
name: github-actions-triage
description: Use when diagnosing failed or pending GitHub Actions runs for CK-NEXUS pull requests and commits.
---

# GitHub Actions triage

1. Confirm repository, PR number, head SHA, base SHA, and the latest run for that exact head.
2. Inspect failed job summaries/logs; do not diagnose from a stale run or a different commit.
3. Reproduce locally when feasible and record environment differences.
4. Classify each failure: code, tests, lint/format, security scanner, dependency audit, external service, permissions, or workflow/configuration.
5. Fix the underlying cause. Do not skip, neutralize, or downgrade required checks to obtain a green result.
6. After pushing, confirm the remote branch SHA and wait for CI on the new SHA; old run results do not validate the new commit.
7. Report check name, run URL, commit SHA, result, and any remaining blocker.
