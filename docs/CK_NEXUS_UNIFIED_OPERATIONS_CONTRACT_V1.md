# CK-NEXUS Unified Operations Contract V1

Status: DEVELOPMENT GOVERNANCE CONTRACT
Authority: CK-NEXUS
Production authority effect: NONE

## 1. Purpose

This contract defines the common operating language for every development AI,
tool, agent, reviewer, and control surface participating in CK-NEXUS.

A new participant must read this contract and the latest live development
snapshot before taking work.

## 2. Central Controller and eight canonical units

The existing Unified Control Surface defines eight top-level units:

1. `core` — AI & Creator Core
2. `skills` — AGNES Skills & Automation
3. `development` — Development Council & Codex
4. `integrations` — Integration & Connector Network
5. `communication` — Email & Communication
6. `data` — Data, Memory & Knowledge
7. `governance` — Governance & Security
8. `operations` — Operations & Commerce

These are navigation and responsibility boundaries. They do not create eight
independent authorities. CK-NEXUS remains the system authority.

## 3. Development workflow states

Canonical sequence:

`RECEIVED -> PLANNED -> QUEUED -> RUNNING -> MEASURED -> REVIEW_REQUIRED -> COMPLETED`

`BLOCKED` is a fail-closed side state.

Rules:
- no stage skipping
- RUNNING requires assigned work
- BLOCKED requires an explicit reason
- MEASURED means evidence/tests exist; it does not mean verified
- REVIEW_REQUIRED cannot be self-approved
- COMPLETED requires recorded human review and merge
- review findings may return a task from REVIEW_REQUIRED to RUNNING

## 4. Live status truth

The live dashboard must separate:
- completed
- active
- queued
- blocked
- competency
- release authority
- measured scores

The system must never invent:
- progress percentage
- ETA
- OpenSSF score
- verification state
- evidence links
- reviewer identity

Unknown values are represented as `UNKNOWN` or null.

Freshness target: <= 10 seconds.
Current Web implementation polls every 5 seconds.

## 5. Evidence semantics

Terms are not interchangeable:

- IMPLEMENTED: code exists
- MEASURED: a test/measurement exists
- REVIEW_REQUIRED: independent review is pending
- COMPLETED: development workflow completed after human review and merge
- VERIFIED: only the authority-specific verification process may use this term

Development evidence is never promoted automatically into Q10 or Production
evidence.

## 6. AI Competency Gate

Dynamic development AI must pass the owner-defined four-level competency gate.

Levels:
- PRO_LEVEL
- OBSERVER
- NOT_ELIGIBLE

A PRO_LEVEL score alone is not write authority. Development write authority
requires separate HUMAN confirmation through the human-approval boundary.

Allowed for a human-confirmed PRO_LEVEL AI:
- read live status
- claim an assigned task
- work on a development branch
- run tests
- open a Draft PR
- propose changes

Never granted by competency:
- merge main
- deploy Production
- mutate Q10/Q11/Q12
- self-approve
- act as independent HUMAN reviewer
- act as Owner

## 7. Collaboration protocol

Before work:
1. read latest live snapshot
2. verify competency permission
3. accept an assigned/queued task
4. transition the task to RUNNING

During work:
1. remain inside assigned scope
2. record meaningful state changes
3. mark BLOCKED immediately with a reason
4. preserve branch isolation
5. preserve evidence and provenance

After work:
1. run measurement/tests
2. transition to MEASURED
3. open/update Draft PR
4. transition to REVIEW_REQUIRED
5. wait for human review
6. after approved merge, record COMPLETED

## 8. Authority boundary

Fail-closed development fallback:
- Q10: NOT_VERIFIED
- Q11: BLOCKED
- Q12: BLOCKED
- Production: NO-GO / NOT CERTIFIED

The collaborative development framework displays these values but does not own
or change release authority.

## 9. Single source of truth

Development state:
`CKNEXUS_DEVELOPMENT_STATUS_DB`

Default:
`~/.local/state/ck-nexus/development-status.sqlite3`

Surfaces:
- Web: `/control`
- API: `/api/control/development/*`
- Terminal: `python scripts/development_status.py`

History is append-oriented in the event ledger.

## 10. Core rule

Search first. Reuse before creating. Deduplicate. Measure. Review security.
Require independent verification where applicable. Adopt canonically only after
the required authority gates pass.

Latest exact evidence wins.
