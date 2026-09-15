# CK-NEXUS Collaborative Development Framework V1

Status: DEVELOPMENT CANDIDATE
Authority effect: NONE
Production: NO-GO

## Purpose

This framework makes development state and AI participation rules machine-enforceable.
It extends the existing Unified Control Surface instead of creating a second control plane.

## Single source of truth

The V1 source of truth is a SQLite development ledger:

`CKNEXUS_DEVELOPMENT_STATUS_DB`

Default:

`~/.local/state/ck-nexus/development-status.sqlite3`

The same ledger is read by:
- Web: `/control`
- API: `/api/control/development/*`
- Terminal/VPS: `python scripts/development_status.py`
- future connected AI adapters

History is append-oriented in the `events` table.

## Live-status freshness

The Web control surface refreshes every 5 seconds.
The declared freshness target is <= 10 seconds.

Unknown data is represented as `UNKNOWN` / null. The system must not invent:
- progress percentages
- ETA
- OpenSSF score
- verification state

## Development task state machine

Canonical sequence:

`RECEIVED -> PLANNED -> QUEUED -> RUNNING -> MEASURED -> REVIEW_REQUIRED -> COMPLETED`

`BLOCKED` is a fail-closed side state and requires a reason.

Skipping stages is rejected.

A task can move from REVIEW_REQUIRED back to RUNNING when review requires changes.

COMPLETED is denied unless:
- human review is recorded
- merge is recorded

AI cannot self-complete a task through this gate.

## AI Competency Gate

Criteria preserve the owner-defined four levels:

Level 1:
- Unified Operations Contract
- Central Controller structure
- workflow states
- authority prohibitions
- live-status reading
- role boundary

Level 2:
- Git / PR / branch / merge
- Development vs Production
- CI/CD
- secure coding
- SAST / dependency / secret scanning
- evidence hashes / signatures / history
- root-cause and durable remediation

Level 3:
- assigned work only
- report results
- report blockers
- accept review
- follow sequence
- respect authority boundary

Level 4:
- OpenSSF Scorecard
- OWASP Top 10
- secret management
- least privilege
- data classification

Decision:
- PRO_LEVEL: score >= 85, Levels 1-3 all pass, Level 4 >= 80%
- OBSERVER: score >= 70 but PRO requirements not met
- NOT_ELIGIBLE: score < 70

Important enforcement detail:
An automated or AI evaluation may calculate a PRO_LEVEL score, but write authority is not activated until a HUMAN confirmation is recorded. This preserves the no-self-approval rule.

PRO_LEVEL write permissions are limited to Development:
- claim assigned task
- write development branch
- run tests
- open Draft PR
- propose change

Competency never grants:
- merge main
- Production deployment
- Q10/Q11/Q12 status mutation
- self-approval

Those remain separate authority gates.

## Release state

V1 displays a fail-closed framework fallback:
- Q10 NOT_VERIFIED
- Q11 BLOCKED
- Q12 BLOCKED
- Production NO-GO / NOT CERTIFIED

The snapshot explicitly labels this source as `fail_closed_framework_default`.
A later adapter must bind these fields to the canonical authority source. This framework itself is not release authority.

## API

Read:
- `GET /api/control/development/live`
- `GET /api/control/development/history`
- `GET /api/control/development/competency/criteria`

Mutation:
- `POST /api/control/development/tasks`
- `POST /api/control/development/tasks/{task_id}/transition`
- `POST /api/control/development/competency/evaluate`

All routes reuse the existing Unified Control access-token boundary.

## Terminal

```bash
python scripts/development_status.py
python scripts/development_status.py --json
python scripts/development_status.py --history 50
```

## Collaboration rule

All AI contributors are subject to the same competency gate, but authority roles are not interchangeable.

Equality of competency requirements does not mean an AI can become:
- independent human reviewer
- Owner
- Production release authority

Latest exact evidence wins.


## Mutation authority

Reading live status uses the existing Unified Control access-token boundary.

Development mutation requires an explicit actor type:

- `actor_type=ai`: requires `competency_agent_id` whose stored assessment is
  human-confirmed `PRO_LEVEL` with development write authority.
- `actor_type=human`: requires the separate
  `CKNEXUS_HUMAN_APPROVAL_TOKEN` boundary.

The human-approval token is separate from the ordinary control token. If it is
not configured, human approval actions fail closed.

Only a HUMAN actor using the separate approval boundary may record a transition
to `COMPLETED`. `human_reviewed` and `merged` must both be literal boolean
true values.

Dynamic external AI admission uses `TeamDirector.admit_agent()`, which checks
the same competency SSOT and appends the admission decision to the event
ledger. `TeamDirector.add_agent()` remains an internal/bootstrap compatibility
path and must not be exposed as an external admission API.

No credential or token value belongs in Git, status output, event history, or
evidence.
