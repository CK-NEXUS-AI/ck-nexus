# Skill Foundry — First Implemented Slice

## Status

- Module: `creator_app/skill_foundry.py`
- Tests: `tests/test_skill_foundry.py`
- Persistence: existing append-only, SHA-256 hash-chained AGNES ledger.
- Runtime activation: deliberately not connected.
- Execution: this module does not execute prompts, scripts, shell commands, tools or model calls.

## What is implemented

1. **Skill Contract** — stable skill ID, semantic version, owner, purpose, object input/output schemas, required and forbidden capabilities, risk, approval policy, evidence requirements, source lineage, license basis and optional rollback version.
2. **Permission-scoped source record** — source identifier/type/title, source URI, declared permission basis and SHA-256 of source content. Raw source content is not stored by the Foundry.
3. **Synthetic evaluation plan** — at least four evaluation dimensions are required: positive, negative, boundary and adversarial. Cases reference `fixture://` data, not pasted customer records.
4. **Quarantine-first registration** — new drafts are recorded as `QUARANTINED` with a canonical draft hash.
5. **Evidence-bound evaluation** — each case must have exactly one result and a SHA-256 evidence reference. Failed tests remain quarantined; passing tests become `EVALUATED`, not active.
6. **Human-review request** — only a matching passed evaluation event in the valid local ledger can be referenced. The event remains `HUMAN_REVIEW_REQUIRED`; activation is explicitly false.

## Lifecycle

`DRAFT → QUARANTINED → EVALUATED → HUMAN_REVIEW_REQUIRED → (separate approval and runtime integration)`

No method in this module can approve, activate, publish, install or execute a skill. A passing evaluation is not proof that the proposed skill is safe for production.

## Safety limits

- Globally forbidden required capabilities include credential export, approval/release-gate mutation, unrestricted shell, arbitrary network and production deploy.
- External-write and high-impact skills cannot declare an approval policy of `none`.
- Source permission basis must be one of `user_provided`, `public_authorized`, `official_documentation`, or `internal_authorized`. This is a declared basis, not independent proof of legal rights; reviewer verification is still required.
- Evidence references are format-checked as SHA-256 values. The Foundry does not independently verify external evidence files or source rights.
- Ledger integrity is checked before human review is requested. The underlying ledger is a local JSONL append-only store, not a distributed multi-host transaction system.

## Intentionally not implemented yet

- No public API route: authentication/authorization and tenant scoping have not yet been verified for this new write surface.
- No automatic prompt extraction from Facebook or other communities.
- No model-generated skill creation or external code import.
- No skill activation, deployment, marketplace publication or automatic agent permission grants.
- No multi-tenant durable registry or distributed concurrency/idempotency guarantees.

## Verification performed

- `python -m py_compile creator_app/skill_foundry.py tests/test_skill_foundry.py`
- `python -m pytest -q tests/test_skill_foundry.py`
- Full AGNES/control-plane regression collection could not run in the current Termux Python environment because FastAPI is not installed. No dependencies were installed.
- Ruff is unavailable in the current Termux Python environment; formatting/lint verification remains outstanding.
