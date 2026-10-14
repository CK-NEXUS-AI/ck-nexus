# AI Product Factory Harvester Patch Validation — 2026-10-15

## Scope
Read-only diagnosis identified that `scripts/ai_github_harvester.py` calls `gh api search/repositories` with form fields but without an explicit HTTP method. A local VPS reproduction previously observed the implicit-method form return HTTP 404 while the same request with `-X GET` returned a successful response. Historical workflow logs only expose the generic `github_search_failed` error because stderr is suppressed; therefore the exact historical HTTP response is not independently proven for every failed run.

## Isolated patch prepared
- Working copy was checked out at canonical main SHA `cb612b72304246781b7dab48dad77d227c40d45d`.
- Local-only change: add `-X GET` to the `gh api` argument list in `scripts/ai_github_harvester.py`.
- Added local-only `tests/test_ai_github_harvester.py` tests for explicit GET/query/limit preservation and fail-closed behavior on command failure.
- No source code was pushed, no PR was opened, no workflow was triggered, and `main` was not modified.

## Validation evidence
- `python3 -m pytest -q tests/test_ai_github_harvester.py`: **2 passed**.
- `python3 -m pytest -q tests/test_ai_github_harvester.py tests/test_ai_product_factory.py`: **7 passed, 1 warning**. The warning was `PytestConfigWarning: Unknown config option: asyncio_mode` because this isolated invocation did not include `pytest-asyncio`; the exercised tests still passed.
- `ruff check scripts/ai_github_harvester.py tests/test_ai_github_harvester.py`: **All checks passed**.
- `python3 -m py_compile scripts/ai_github_harvester.py tests/test_ai_github_harvester.py`: passed.
- `git diff --check`: passed.

## Status and limitations
Patch status is **locally validated**, not merged, CI-validated, or production-verified. No live workflow was triggered. A full repository test suite was not run. Production remains **NO-GO** until authorized review, CI evidence, and applicable release gates are complete.
