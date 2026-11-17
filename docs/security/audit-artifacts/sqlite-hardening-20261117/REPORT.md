# SQLite Hardening Evidence

Repository: `CK-NEXUS-AI/ck-nexus`
Branch: `security/sqlite-hardening-20261117`
Base: `main` at `4d1366cef3cbdd18aa174bdf67308567635c750a`
PR: [#374 — Harden local SQLite database paths and sidecars](https://github.com/CK-NEXUS-AI/ck-nexus/pull/374)

This PR isolates SQLite hardening from the wider integration bundle in PR #373. It changes **7 files** relative to `main`: the shared SQLite opener, two database integrations, two test files, and the evidence report/manifest.

## Verification on VPS

- Full repository pytest suite on this isolated branch: **1,004 passed, 2 skipped** (59.81s; exit 0).
- Ruff check on all five changed Python source/test files: PASS.
- `git diff --check`: PASS.
- Bandit targeted scan on the three changed source files: exit 0; no findings reported.
- pip-audit: no known vulnerabilities reported; local package `ck-nexus-creator` could not be audited from PyPI.
- Regression tests cover symlinked `-journal`, `-shm`, existing `-wal`, and deterministic database-path replacement immediately before `sqlite3.connect`.
- The deterministic path-replacement test confirms detection of that controlled replacement. It is **not** a concurrent TOCTOU stress test and does not prove protection against hostile processes running under the same UID.

## Independent review limitations

No fresh independent review of this isolated seven-file candidate has been completed. The previous Codex review covered an earlier five-file SQLite snapshot only, before the journal/SHM and deterministic path-swap regressions were added. A full review of PR #374 remains required before merge.

The same-UID process trust boundary remains unchanged. Do not interpret the controlled path-swap regression as proof against concurrent hostile same-UID processes.

## PR, CI, and release status (observed 2026-11-17)

| Item | Verified status |
|---|---|
| PR #374 | OPEN |
| Changed files | 7 |
| GitHub Actions | BLOCKED — billing lock; jobs did not start |
| Independent review | NOT VERIFIED |
| Merge | NOT MERGED |
| Deployment | NOT DEPLOYED |
| Q10–Q16 | NOT CLOSED / NOT VERIFIED |
| Production readiness | **NO-GO** |

The PR #374 check-run annotations state: `The job was not started because your account is locked due to a billing issue.` This is an account-level block, not a code-test failure. No alternate account has been used to bypass it.

PR #373 remains open as a separate, broader 60-file integration bundle. Its SQLite changes are duplicated in the focused PR #374; PR #373 must be reviewed independently and must not be treated as verified by PR #374's test results.

## SHA-256

The manifest records SHA-256 hashes and byte sizes for the five changed Python source/test files in this isolated branch.
