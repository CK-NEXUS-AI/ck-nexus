# SQLite Hardening Evidence

Repository: `CK-NEXUS-AI/ck-nexus`
Branch: `security/sqlite-hardening-20261117`
Base: `origin/main` at `4d1366cef3cbdd18aa174bdf67308567635c750a`

This candidate isolates the SQLite hardening change from the wider 60-file integration bundle previously proposed in PR #373. It changes **7 files** only: the shared SQLite opener, two database integrations, two test files, and the evidence report/manifest.

## Verification on VPS

- Full repository pytest suite on this isolated branch: **1,004 passed, 2 skipped** (59.81s; exit 0).
- Ruff check on the five changed Python source/test files: PASS.
- `git diff --check`: PASS.
- Regression coverage includes direct rejection of symlinked `-journal` and `-shm` sidecars, existing `-wal` symlink coverage, and a deterministic database-path replacement immediately before `sqlite3.connect`.
- The path-replacement test confirms detection of that controlled replacement. It is **not** a concurrent race stress test and does not prove protection against hostile processes running under the same UID.
- Previous source-snapshot security evidence: Bandit 0 high / 0 medium / 0 low; pip-audit 0 known vulnerabilities among 84 audited dependencies, with local package `ck-nexus-creator` not auditable from PyPI. These prior results have not been rerun on this isolated branch.

## Independent review limitations

No fresh independent review of this isolated branch has been completed. The earlier Codex review covered only an earlier five-file SQLite snapshot, before the journal/SHM and deterministic path-swap regressions were added. A full review of this isolated seven-file candidate remains required before merge.

The same-UID process trust boundary remains unchanged. Do not interpret the controlled path-swap regression as proof against concurrent hostile same-UID processes.

## PR, CI, and release status

| Item | Verified status |
|---|---|
| Isolated branch | `security/sqlite-hardening-20261117` |
| Changed files | 7 |
| GitHub PR | NOT CREATED YET |
| GitHub Actions | Previously BLOCKED — billing lock; isolated branch checks not yet observed |
| Independent review | NOT VERIFIED |
| Merge | NOT MERGED |
| Deployment | NOT DEPLOYED |
| Q10–Q16 | NOT CLOSED / NOT VERIFIED |
| Production readiness | **NO-GO** |

The prior GitHub check-run annotations stated: `The job was not started because your account is locked due to a billing issue.` This is an account-level block, not a code-test failure. No alternate account has been used to bypass it.

## SHA-256

The manifest records SHA-256 hashes and byte sizes for the five changed Python source/test files in this isolated branch.
