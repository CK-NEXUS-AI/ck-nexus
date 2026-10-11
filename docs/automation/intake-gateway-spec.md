# CK-NEXUS Automation Intake and Evidence Routing

**Status:** DESIGN SPECIFICATION ONLY — not implemented, not executed, not verified, not production.

## Objective

Keep mobile devices as a lightweight command/approval surface. Use n8n Cloud for orchestration, Microsoft 365/OneDrive for approved records, GitHub for reviewed engineering artifacts, and the VPS only for workloads that require a private runtime.

## Target flow

`ChatGPT / approved operator command → authenticated intake → schema validation → sensitivity screening → policy/approval gate → destination-specific writer → evidence receipt`

- **n8n Cloud:** orchestration, retries, routing, notifications, and execution history.
- **Microsoft 365 / OneDrive:** canonical records, operational reports, sanitized evidence, and archives.
- **GitHub:** code, sanitized engineering reports, test definitions, and reviewed release artifacts. Use a dedicated branch and pull request; never auto-commit arbitrary inbound payloads to `main`.
- **VPS:** optional private worker for tasks that cannot run in n8n Cloud. Do not expose an unauthenticated administrative endpoint or install a second service without checking existing services and resource limits.
- **Mobile:** issue commands, review summaries, and approve exceptional actions; avoid local heavy processing.

## Intake contract (v1)

Required fields:

- `schema_version`: exact string `1.0`
- `event_id`: stable unique identifier for idempotency
- `event_type`: one of `status_report`, `gate_status`, `ci_failure`, `security_finding`, `release_candidate`, `recovery_note`
- `source`: bounded source identifier
- `artifact_type`: bounded artifact category
- `summary`: short, sanitized description

Optional fields: `gate`, `status`, `source_url`, `commit_sha`, `approval_required`.

The receiver must use an allowlist, enforce length limits, redact secret-like patterns, validate URLs and commit SHAs, and reject malformed payloads. It must not accept or persist raw email bodies, credentials, access tokens, passwords, private keys, customer PII, or arbitrary file contents.

## Required security controls

1. Require header authentication (or stronger supported authentication) before publishing the webhook.
2. Keep the workflow inactive until the auth credential is configured and negative/positive tests pass.
3. Use idempotency on `event_id`; repeated events must not create duplicate records or PRs.
4. Keep raw payloads out of successful and error execution retention where supported; persist only sanitized metadata.
5. Apply a destination policy before every write. Personal data and secrets must never be copied to GitHub.
6. Write GitHub artifacts to a dedicated branch and open a PR. Never bypass CI, branch protection, review, or release gates.
7. Require human approval for destructive actions, external communications, privileged changes, production deployments, or changes to Q10–Q16 evidence.
8. Keep status states distinct: `DESIGNED`, `IMPLEMENTED`, `EXECUTED`, `VERIFIED`, `PRODUCTION`. Do not infer one from another.
9. Emit an evidence receipt with event ID, destination, result, timestamp, and relevant commit/release identity. Never include secrets in the receipt.

## OneDrive information architecture

Create only in the verified target account:

- `CK-NEXUS-CONTROL-CENTER/00_INBOX`
- `CK-NEXUS-CONTROL-CENTER/01_PROJECT-RECORDS`
- `CK-NEXUS-CONTROL-CENTER/02_ENGINEERING-EVIDENCE`
- `CK-NEXUS-CONTROL-CENTER/03_Q10-Q16-GATES`
- `CK-NEXUS-CONTROL-CENTER/04_DAILY-REPORTS`
- `CK-NEXUS-CONTROL-CENTER/05_GITHUB-RELEASES`
- `CK-NEXUS-CONTROL-CENTER/06_ERRORS-AND-RECOVERY`
- `CK-NEXUS-CONTROL-CENTER/99_ARCHIVE`

Do not create these folders until the connected Microsoft identity is confirmed to be the intended account. The folder list is a proposed layout, not evidence that folders already exist.

## Rollout gates

- [ ] Confirm Microsoft identity and OneDrive destination.
- [ ] Create folders and perform write → read-back → delete test in that verified destination.
- [ ] Configure a unique webhook path and header-auth credential in n8n.
- [ ] Test missing/wrong auth, malformed schema, duplicate event, secret-redaction cases, and normal sanitized event.
- [ ] Add durable OneDrive storage using a dedicated credential with least privilege.
- [ ] Add GitHub routing only for approved engineering artifact types, using a branch/PR rather than direct writes to `main`.
- [ ] Add VPS forwarding only if required; verify TLS, auth, firewall/IP restrictions, request-size limits, and resource usage.
- [ ] Verify every route from its actual trigger through destination read-back and evidence receipt.
- [ ] Keep production status NO-GO until all applicable CK-NEXUS release/security gates pass.

## Current implementation boundary

This document is a plan. A workflow draft, endpoint, credential, OneDrive folder, GitHub automation, or VPS service must not be reported as implemented unless the relevant tool returns success and a follow-up read-back verifies it.
