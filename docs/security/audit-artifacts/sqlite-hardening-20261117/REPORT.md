# SQLite Hardening Evidence

Repository: `CK-NEXUS-AI/ck-nexus`
Branch: `security/sqlite-hardening-20261117`
Base: `main` at `4d1366cef3cbdd18aa174bdf67308567635c750a`
PR: [#374 — Harden local SQLite database paths and sidecars](https://github.com/CK-NEXUS-AI/ck-nexus/pull/374)

This PR isolates SQLite hardening from the wider integration bundle in PR #373. The candidate now changes **8 files** relative to `main`: four Python modules, two test files, and the evidence report/manifest.

## Verification on VPS

- Full repository pytest suite: **1,008 passed, 2 skipped** (70.54s; exit 0; 12 deprecation warnings).
- Ruff lint check on all six changed Python source/test files: PASS.
- Ruff formatter check: NOT RUN in this verification pass.
- `git diff --check`: PASS.
- Bandit targeted scan on the four changed Python modules: exit 0; no findings reported.
- pip-audit: no known vulnerabilities reported among auditable packages; local package `ck-nexus-creator` could not be audited from PyPI.

## Review-driven fixes

- Existing owned database directories are tightened to mode 0700 using an opened directory descriptor; the path/inode is rechecked after tightening.
- EbookKnowledgeStore construction and read-only queries no longer create missing parent directories. Directory creation/tightening occurs on the write initialization path.
- Explicit `isolation_level` is forwarded to read-only SQLite connections.
- BrainRuntime and BrainJournal consistently expand `~` journal paths.
- The missing-`O_NOFOLLOW` regression test now works on platforms where the attribute is absent.
- The Q10–Q16 status table links to the [Q10–Q16 Closure Contract](../../../Q10_Q16_CLOSURE_CONTRACT.md).

## Sidecar and TOCTOU boundary

- Regression tests cover symlinked `-journal`, `-shm`, existing `-wal`, and deterministic database-path replacement immediately before `sqlite3.connect`.
- The deterministic path-replacement test confirms detection of that controlled replacement. It is **not** a concurrent TOCTOU stress test.
- Existing sidecars and sidecars visible during connection setup are checked. SQLite may create WAL/SHM later on first use; the private 0700 parent directory is the cross-UID protection boundary for those later creations. Hostile processes running under the same UID remain inside the documented trust boundary.

## Independent review status

Cubic's previous AI review identified seven issues. The fixes above address the reported cases; its re-review of the latest pushed commit had inspected all eight files but remained `in_progress` at the time of this evidence update. A fresh read-only Codex CLI review of commit `54510a9` reported no actionable defects; it included one speculative P1 note that the reviewer itself qualified as not a direct issue. This review does not replace hosted CI or the pending Cubic re-review.

## PR, CI, and release status

| Item | Verified status |
|---|---|
| PR #374 | OPEN |
| Changed files | 8 |
| GitHub Actions | BLOCKED — billing lock; jobs did not start |
| Cubic re-review | IN PROGRESS — 8/8 files inspected |
| Independent Codex review | COMPLETE — no actionable findings on `54510a9` |
| Merge | NOT MERGED |
| Deployment | NOT DEPLOYED |
| Q10–Q16 | NOT CLOSED / NOT VERIFIED |
| Production readiness | **NO-GO** |

The PR #374 check-run annotations state: `The job was not started because your account is locked due to a billing issue.` This is an account-level block, not a code-test failure. No alternate GitHub account has been used to bypass it.

PR #373 remains open as a separate, broader 60-file integration bundle. Its SQLite changes overlap the focused PR #374; PR #373 must be reviewed independently and must not be treated as verified by PR #374's test results.
