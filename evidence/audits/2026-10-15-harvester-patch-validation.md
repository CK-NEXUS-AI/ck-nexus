# AI Product Factory Harvester — Isolated Patch Validation

Date: 2026-10-15 UTC
Base: `cb612b72304246781b7dab48dad77d227c40d45d`
Scope: local isolated scratch directory only; no Git branch created, no source code pushed, no Actions workflow triggered, no `main` changes.

## Change prepared locally

- In `scripts/ai_github_harvester.py`, command construction was changed from `gh api search/repositories ...` to `gh api -X GET search/repositories ...`.
- Added a regression test to `tests/test_ai_product_factory.py` that mocks `subprocess.run` and asserts the method and endpoint arguments.
- Scratch patch file SHA-256:
  - harvester: `2dc4d24ef85926163908746eebb402e8081d0ae80aead959f22f48abb061100f`
  - test file: `bb40a12efd83d7a4f653518718146cf1499ea75ac3c22538ae46891d01ad6b2e`

## Validation performed

- Python syntax compilation: PASS.
- Isolated mocked call verifies explicit `GET`, endpoint, and empty JSON response parsing: PASS.
- Full pytest suite: NOT RUN; `pytest` is not installed in the active VPS Python environment. No dependency installation was attempted.
- GitHub Actions CI after patch: NOT RUN.
- Live harvester against GitHub from the workflow runner: NOT VERIFIED.

## Result

Patch is prepared and has limited local smoke evidence only. This is not a complete regression-test pass, CI pass, or deployed fix. Source patch remains in `/tmp/cknexus-harvester-fix` on the VPS and was not pushed to GitHub. Next safe engineering step is to apply this narrow patch on a dedicated branch in an approved working repository, run the project test suite, then open a PR for review; do not merge without required independent review and green checks.

Production status remains `NO-GO`.