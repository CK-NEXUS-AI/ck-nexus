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
