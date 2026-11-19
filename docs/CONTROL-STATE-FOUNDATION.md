# CK-NEXUS Control State Foundation

**Status:** Architecture/design proposal only — not deployed, migrated, or production-approved.  
**Related review:** [PR #290 — Master Recovery Ledger](https://github.com/spinlnw10-art/ck-nexus/pull/290)  
**Snapshot date:** 2026-10-12

## Goal

Create a machine-readable, auditable state store so automation can consume bounded facts without treating Markdown, workflow execution success, or candidate CI as blanket proof of health. Build a read-only surface first. Do not begin self-healing automation in this phase.

## Canonical state and provenance

Each status assertion must include:
- subject type and immutable subject ID
- status from a controlled vocabulary
- observed time (UTC), source system, source record ID and evidence URI/reference
- source revision/version when applicable
- verifier/collector identity and verification scope
- expiry/staleness policy
- limitations and sanitized reason
- correlation/incident ID where applicable

Never store credential payloads or email contents. Store secret-manager references only. The control database must not silently overwrite evidence; retain audit history and superseding events.

## Proposed tables

| Table | Purpose | Write policy |
|---|---|---|
| `workflow_registry` | n8n workflow ID, name, active flag, version, last observed execution | Collector updates append observation history |
| `credential_registry` | Credential ID/name/type/owner reference/scopes/status; no secret fields | Metadata only; explicit verification events |
| `incident_registry` | Incident ID, severity, status, hypothesis, owner, timestamps | State transitions audited |
| `approval_registry` | Human approval for a bounded action, target, expiry and decision | Append-only decisions; revocation supported |
| `audit_registry` | Append-only actor/action/target/decision/time/correlation/evidence | No ordinary update/delete |
| `production_gate_registry` | Gate ID, status, release identity, evidence refs, verifier, timestamp | Gate status tied to immutable release identity |
| `evidence_registry` | Evidence type, source ID, digest, storage reference, signer/verifier metadata | Never claim digest/signature without actual computation and verification |

## State vocabulary

- `VERIFIED`: evidence satisfies the specific assertion and scope.
- `EXECUTED`: a recorded execution occurred; result can still be insufficient.
- `NOT_VERIFIED`: evidence absent/incomplete/stale/ambiguous.
- `BLOCKED`: a known prerequisite prevents verification.
- `DISABLED`: deliberately not enabled.
- `REVOKED`: previously valid authorization or credential reference revoked.
- `PRODUCTION`: separate release decision, not a credential/workflow status. Current CK-NEXUS release decision remains `NO_GO`.

Do not use an aggregate percentage without defined denominator, scoring rules, timestamp and evidence coverage. Do not promote a gate from component results.

## Proposed read-only API

- `GET /health`: service/process health only; must not imply CK-NEXUS production readiness.
- `GET /readiness`: summarizes workflow/credential/incident/gate statuses with freshness timestamps and limitations.
- `GET /evidence`: returns sanitized evidence metadata, source IDs, digests and execution IDs, never raw secrets or email contents.

All endpoints require authenticated, least-privilege access; responses should be bounded, paginated where needed, versioned, and include `observed_at`, `as_of`, `stale`, `source`, and `limitations`. Read-only endpoints must have no side effects.

## Suggested implementation order

1. Review and adopt the documentation in a normal PR.
2. Implement the PostgreSQL schema in a disposable local/CI database; validate migrations and constraints.
3. Add a read-only collector for n8n metadata with strict secret-field allowlisting.
4. Add evidence provenance and append-only audit events.
5. Implement authenticated read-only API endpoints and contract tests.
6. Run threat model, authorization tests, redaction tests, and migration/restore tests.
7. Only after independent review consider any write/action endpoint. Self-healing is out of scope.

## Explicit non-goals

- No live PostgreSQL deployment or production database mutation.
- No automatic activation/editing of n8n workflows.
- No email send, draft, delete, reply or attachment download.
- No secret/token ingestion into the database.
- No claim that a health API is “connected to ChatGPT immediately” without authenticated integration and an access-control review.
- No production readiness percentage without an approved, evidence-backed scoring model.
