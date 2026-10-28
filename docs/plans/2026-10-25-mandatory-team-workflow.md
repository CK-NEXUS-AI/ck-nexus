# Mandatory Team Workflow Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a named research/design/implementation/review/test/synthesis workflow for every Auto Developer task and preserve truthful evidence about whether independent agents actually participated.

**Architecture:** Extend the existing Auto Developer prompt contract and evidence record rather than rebuilding the existing AI team, debate, or Capability Authority modules. Keep real independent-voter claims separate from single-agent multi-perspective work.

**Tech Stack:** Python 3.12, pytest, existing Auto Developer, Markdown specifications.

## Global Constraints

- Preserve all existing user changes and do not reset, stash, clean, or overwrite the primary checkout.
- Keep the primary checkout read-only to the coding agent; use the existing isolated worktree flow.
- AI votes do not bypass Capability Authority, policy, evidence, secret/path checks, or high-risk approval gates.
- Do not claim independent agents unless separate live provider/session evidence exists.
- Do not stage all files or publish, merge to `main`, or deploy to production as part of this change.

---

### Task 1: Define the mandatory role contract

**Files:**
- Create: `docs/specs/2026-10-25-mandatory-team-workflow.md`
- Create: `docs/plans/2026-10-25-mandatory-team-workflow.md`

**Interfaces:**
- The specification defines six required roles and the output fields each role must return.

- [x] Record the sequence, independence rules, evidence requirements, and authority boundary.

### Task 2: Enforce the prompt contract and evidence labels

**Files:**
- Modify: `creator_app/n8n_intelligence/auto_developer.py`
- Modify: `tests/test_n8n_auto_developer.py`

**Interfaces:**
- `AutoDeveloper._prompt(payload) -> str` includes the six role stages, role output schema, source-evidence requirement, independent-voter limitations, and safety boundary.
- Each Auto Developer evidence record states `team_workflow_required=true`, `team_execution_mode=single-agent-multi-perspective`, `independent_council_vote=false`, and the required role list. This is truthful because the current runner invokes one Codex CLI session, not six independent providers.

- [x] Add a prompt-contract test and observe it fail before implementation.
- [x] Add evidence-field assertions and observe them fail before implementation.
- [x] Implement the minimum prompt/evidence change.
- [x] Run ` .venv/bin/pytest -q tests/test_n8n_auto_developer.py` and confirm the focused suite passes.

### Task 3: Verify integration and preserve existing changes

**Files:**
- Test: `tests/test_n8n_auto_developer.py`
- Check: `creator_app/n8n_intelligence/auto_developer.py`

- [x] Run relevant regression tests and Ruff on changed Python files.
- [x] Run `git diff --check` and inspect the final diff/status without staging or committing unrelated files.
- [x] Report exact verification results and clearly label the current execution mode as single-agent multi-perspective.

## Unresolved operational boundary

The current Auto Developer can enforce a structured multi-perspective process in its prompt and record truthful execution-mode evidence. It cannot itself prove that separate live AI providers participated. A future independent Council adapter must supply provider/session identity, health/quota evidence, eligible-voter calculation, vote receipts, and quorum enforcement before the system may claim a real multi-agent vote.
