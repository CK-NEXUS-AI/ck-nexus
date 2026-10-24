# CK-NEXUS Development Council

Status: Release Candidate capability. This document describes the advisory multi-agent layer; it is not evidence of Production readiness.

## Purpose

The Development Council gives CK-NEXUS one user-facing lead orchestrator plus five bounded specialist advisers for development discussion, research, design, analysis, implementation planning, and critical review.

| ID | Adviser | Primary job | Hosted web search | Side effects |
|---|---|---|---|---|
| `architect` | Architect & Strategist | Architecture, strategy, requirements, roadmap, trade-offs | No | None |
| `research` | Research & Analyst | Current research, verification, comparisons, evidence synthesis | Yes | None |
| `designer` | Product & UX Designer | UX flows, information architecture, interaction and product design | No | None |
| `builder` | Engineering & Automation Builder | Backend/API/integration/automation implementation planning | No | None |
| `reviewer` | Security / QA / DevOps Reviewer | Security, QA, reliability, deployment, production gates | No | None |

## Orchestration

The manager pattern uses Agents-as-tools. `CK-NEXUS Lead Orchestrator` owns the final answer and may consult the specialist agents as bounded tools. In `auto` mode it must consult at least two relevant specialists; in `council` mode it consults all five. A focused mode can call one specialist directly.

The advisory team cannot mutate code, infrastructure, accounts, permissions, production data, or external systems. Any real action must pass through a separate CK-NEXUS execution path such as the guarded Codex bridge or an explicit integration action with its own permissions and production gate.

## API

- `GET /api/dev-team` — roster, readiness and policy.
- `POST /api/dev-team/run` — consult the team.

Request fields:

```json
{
  "prompt": "Review the next architecture milestone",
  "session_id": "development-council",
  "consult_mode": "auto",
  "context": "Release Candidate; do not overclaim readiness",
  "language": "ไทย"
}
```

Supported `consult_mode` values: `auto`, `council`, `architect`, `research`, `designer`, `builder`, `reviewer`, `debate`.

## Models

All advisers default to `OPENAI_MODEL`. Each role can be overridden independently without changing source code:

- `CKNEXUS_MODEL_ARCHITECT`
- `CKNEXUS_MODEL_RESEARCH`
- `CKNEXUS_MODEL_DESIGNER`
- `CKNEXUS_MODEL_BUILDER`
- `CKNEXUS_MODEL_REVIEWER`

This creates five model slots while keeping a safe common default. Do not hardcode API keys or model credentials.

## Memory

The lead conversation uses an Agents SDK session prefixed with `dev-team:`. SQLite is used for local/demo deployments; when `CKNEXUS_SESSION_DATABASE_URL` is configured, SQLAlchemy/PostgreSQL session storage is used.

## Research boundary

Only Research & Analyst receives `WebSearchTool`. This keeps the external research surface narrow and makes routing easier to audit. Source verification remains part of the final Orchestrator responsibility.

## Readiness boundary

Mock Mode validates routing contracts and UI/API behavior without API spend. Live multi-agent evidence remains BLOCKED until a server-side `OPENAI_API_KEY` is configured and a live smoke test succeeds. Production readiness still requires the broader CK-NEXUS P0 gate set.


## Debate Protocol V1

`consult_mode=debate` reuses the existing Development Council instead of creating a second agent runtime.

Role mapping:

- PROPOSER -> Architect & Strategist
- OPPOSER -> Security / QA / DevOps Reviewer
- EXAMINER -> Research & Analyst
- SYNTHESIZER -> bounded synthesis agent on the existing Council model
- MODERATOR -> deterministic Python rules, not an authority-bearing model

The deterministic moderator enforces bounded structured turns, a 300-word limit per contribution, duplicate detection, a 0.8 advisory consensus threshold, safety escalation, and explicit non-authority semantics.

Possible moderation states:

- `CONSENSUS_REACHED`
- `MORE_EVIDENCE_REQUIRED`
- `DISAGREEMENT_REMAINS`
- `HUMAN_REVIEW_REQUIRED`

A debate consensus is advisory only. It cannot set VERIFIED, approve its own output, merge code, deploy Production, modify Q10/Q11/Q12, or replace independent human review or owner sign-off.

V1 intentionally keeps live debate on the existing Agents-SDK-capable Council provider. Cross-provider role routing is a separate follow-on after provider registry/model/privacy compatibility is refreshed and measured.

## Mandatory Team Workflow Rule — Research and Engineering (2026-10-25)

This rule applies to every non-trivial research, design, implementation, and verification task. The Lead Orchestrator must assign bounded work to the existing specialist roles before synthesizing a result. It must not silently perform the entire task as a single undifferentiated role.

### Required work split

1. **Research & Analyst** — locate primary sources (official documentation, official repositories, peer-reviewed papers, benchmark owners, and attributable case studies); record access date and exact source URL.
2. **Verification** — independently check each material claim, date, license, pricing, benchmark setup, and current project status; identify contradictions and state the closest verifiable proxy.
3. **Architect & Strategist** — assess architecture, autonomy level, integration fit, migration cost, and alternatives.
4. **Engineering & Automation Builder** — map verified capabilities to a bounded implementation plan; do not edit unrelated files or introduce duplicate runtimes.
5. **Security / QA / DevOps Reviewer** — challenge evidence, inspect threat model and limits, and define acceptance tests and rollback conditions.
6. **Lead Orchestrator** — consolidate only after the specialist findings exist; preserve dissent, cite primary evidence inline, and label unknowns `No public evidence` rather than infer them.

### Participation and vote integrity

- A role name or configured model slot is not proof of an independent live agent. Record agent/provider/model identity and actual response status when available.
- Only eligible, responding, independently sourced voting units count. Do not count duplicate sessions or the same underlying model/provider/account as multiple independent votes without evidence of independence.
- Require a quorum of at least three eligible independent voting units for an automated majority decision. Majority applies only to ordinary, reversible, sandboxed work; it does not override deterministic policy, tests, signed capability grants, or human-only approval gates.
- A provider that is down, unauthorized, or quota-exhausted is `UNAVAILABLE`, not an implicit yes/no vote. If quorum is absent, gather more evidence or report the block.
- Research consensus is not source verification. Worker output remains unverified until the designated independent verifier confirms it.

### Execution and evidence

- Research tasks proceed in the user-specified order; each item receives its own complete report and source list before the next item is synthesized. Large reports may be delivered in sequential installments, but must not merge tools into a shared section.
- Preserve existing working-tree changes. Inspect `git status` before edits; use additive, bounded changes; do not reset, clean, overwrite, merge, or deploy unrelated work.
- For code changes, work in an isolated branch/worktree or approved sandbox, write acceptance tests first where feasible, run targeted tests then relevant regression/security checks, and bind evidence to the exact commit SHA.
- Never claim live capability, benchmark performance, test success, or production readiness without current, reproducible evidence. Keep production mutation and high-risk actions behind their existing authority gates.
- Store reports under `docs/research/tool-reports/` using stable numbered names; record the research date, source URLs, evidence strength, unresolved claims, and CK-NEXUS integration disposition.
