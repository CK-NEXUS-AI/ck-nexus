# CK-NEXUS AI Product Factory — Harvester Failure Follow-up

Date: 2026-10-15 UTC
Scope: Read-only diagnosis; no workflow, source code, repository permissions, or deployment was changed.

## Evidence

- GitHub Actions run: [38607704328](https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/38607704328), scheduled run on main SHA `cb612b72304246781b7dab48dad77d227c40d45d`.
- Failed job: `harvest-and-gate`, job ID `116002736332`; failed step: `Harvest GitHub signals`.
- Raw job log shows `scripts/ai_github_harvester.py` raised `RuntimeError: github_search_failed`; the wrapper intentionally suppresses the underlying subprocess stderr, so the historical runner's exact HTTP response is not directly captured.
- The source at the run's main SHA invokes `gh api search/repositories` with `-f q=...` and `-f per_page=...`, without an explicit HTTP method.
- Read-only reproduction on the authorized VPS: the same implicit-method command returned `gh: Not Found (HTTP 404)` for all three configured query patterns. The otherwise identical command with `gh api -X GET search/repositories ...` succeeded (`total_count=2800` for `topic:ai-agents stars:>100`).

## Diagnosis

**Strongly supported likely root cause:** `gh api` infers a write method when form fields are supplied unless GET is explicitly selected; the repository-search endpoint is a GET endpoint. The implicit request reproduces HTTP 404 while explicit `-X GET` succeeds. Because the historical Actions log does not contain the captured subprocess stderr or HTTP method, label the historical exact cause as `LIKELY_ROOT_CAUSE`, not fully verified for that specific run.

## Safe next action

Prepare a minimal source change to specify `-X GET` and add a regression test that verifies the search command method, then run deterministic tests in an isolated branch. This note does not claim the fix has been implemented, tested, or deployed. Do not trigger the scheduled/manual workflow as part of this read-only audit.

## Gate status

- Diagnosis: `EXECUTED`; reproduction supports likely root cause.
- Source fix: `NOT_IMPLEMENTED`.
- Regression test / CI verification: `NOT_EXECUTED`.
- Production: `NO-GO` unchanged.