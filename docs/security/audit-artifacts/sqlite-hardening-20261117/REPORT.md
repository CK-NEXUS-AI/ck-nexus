# SQLite Hardening Evidence

Branch: `integration/termux-change-sync-policy-20261117`
SQLite baseline commit: `0bd62e097ab2397048a858e93a4b6f1c8bcadf82`
Base parent for the SQLite hardening change: `f7b64885df118cc81183aedce202a5068291d841`

## Verification update

- Full VPS pytest suite after the additional regressions: **1,019 passed, 2 skipped** (70.27s; exit 0).
- Ruff check: PASS.
- Ruff format check: PASS.
- `git diff --check`: PASS.
- Added direct symlink rejection tests for `-journal` and `-shm`; existing `-wal` symlink regression remains.
- Added a deterministic path-swap test that replaces the database path with a symlink immediately before `sqlite3.connect`; the helper detects the changed path/inode and fails closed.
- The path-swap test is a controlled regression test, not a concurrent race stress test. It does not establish protection against hostile processes running under the same UID.
- Previous security evidence remains: Bandit 0 high / 0 medium / 0 low; pip-audit 0 known vulnerabilities among 84 audited dependencies, with one local package not auditable from PyPI; SQLite `PRAGMA quick_check`: `ok`; `cknexus-creator.service`: active; DB directory/file modes `0700` / `0600`.

## Independent review limitations

The original Codex review covered the original five-file SQLite change snapshot only, not the full repository. The new journal/SHM symlink tests and deterministic path-swap test were added after that review and have **not yet received a fresh independent Codex review**. The same-UID process trust boundary remains unchanged.

## PR and CI status (observed 2026-11-17)

| Item | Verified status |
|---|---|
| PR #373 | OPEN |
| PR scope relative to current `origin/main` merge base | 60 files, 10 commits, 2,216 additions, 172 deletions; broader than SQLite hardening alone |
| GitHub Actions | BLOCKED — billing lock; jobs did not start |
| Merge | NOT MERGED |
| Deployment | NOT DEPLOYED |
| Production readiness | NO-GO |
| Q10–Q16 | NOT CLOSED / NOT VERIFIED |

GitHub check-run annotations state: `The job was not started because your account is locked due to a billing issue.` This is an account/billing-level block, not a code-test failure. No alternate account was used to bypass the restriction.

## SHA-256

The manifest records current hashes and byte sizes for the five original SQLite source/test files. The updated `tests/test_brain_runtime.py` hash reflects the added regression tests.
