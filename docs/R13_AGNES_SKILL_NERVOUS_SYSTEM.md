# CK-NEXUS R13 — AGNES Skill Nervous System (Development Candidate)

This branch extends the R9–R11 development candidate without rewriting prior history.

## Objective

Give AGNES a portable, single-file skill brain plus governed "body" interfaces while keeping credentials, side effects, and production authority outside the model.

## Added

- Canonical `creator_app/skills/agnes/SKILL.md` with 18 skills and global invariants.
- Skill discovery/activation registry from the single manifest file.
- Local-first inference readiness: AGNES does not consume a user API key.
- Append-only hash-chained learning ledger with tamper detection.
- Workspace Broker abstraction for local, E2B, GitHub Codespaces, and Daytona.
- Governed 21-step self-upgrade lifecycle with quarantine, evidence, canary, rollback, and append-only learning.
- API: `/api/agnes/status`, `/api/agnes/skills`, `/api/agnes/plan`, `/api/agnes/upgrade-plan`.
- Production mutation remains disabled; R12 staging evidence remains mandatory.

## Credential rule

Skills are instructions/capabilities, not billing credentials. Cloud services still require an authorized account/credential somewhere. AGNES itself receives neither raw user API keys nor bulk credential exports. Local runtimes are the default no-user-key path; cloud credentials, when intentionally enabled later, must remain service-managed behind the Credential Broker.

## External tool discovery rule

MCP/Agent Skills discovery may be automated, but activation is not blind installation. Candidate skills enter quarantine until source identity, version, license, checksum, scripts, requested tools, network egress, and credential scopes have been reviewed.

## Release posture

Development Candidate / RC / NO-GO. This feature does not replace R12 evidence gates.
