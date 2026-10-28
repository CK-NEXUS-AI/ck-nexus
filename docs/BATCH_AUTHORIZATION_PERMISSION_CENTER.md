# CK-NEXUS Batch Authorization Permission Center

Status: implemented as a guarded grant registry and evaluation API; controller-wide enforcement is not yet complete.

## Purpose

Allow a human operator to grant several exact permissions and exact targets in one confirmation, instead of approving each low-risk step separately. Grants are persisted in a dedicated SQLite database beside the configured CK-NEXUS database, with mode `0600`, expiry, audit labels, and revocation.

## UI

Open `/permissions` in the CK-NEXUS web app. The page provides:
- presets for read-only audit, safe autonomous development, and development plus local Git;
- multi-select permissions and system/repository targets;
- explicit duration and API-cost ceiling;
- a separate list of high-impact permissions, each of which must also be in the selected permission set;
- an operator confirmation prompt;
- grant listing and revocation controls.

The access token is held only in page memory and cleared after grant creation. Use HTTPS except on localhost. Do not paste tokens into screenshots, logs, or reports.

## API

All endpoints require a configured `CKNEXUS_ACCESS_TOKEN` and a valid `Authorization: Bearer ...` header.

- `GET /api/permissions/grants` — list persisted grants, including expired/revoked state.
- `POST /api/permissions/grants` — create a batch grant with `grant_id`, `permissions`, `targets`, `approved_by`, `ttl_seconds`, `max_cost_usd`, and optional `high_impact_permissions`.
- `POST /api/permissions/grants/{grant_id}/revoke` — revoke a grant.
- `POST /api/permissions/evaluate` — evaluate one exact permission/target request against active grants.

Wildcard permission and target values are rejected. Grant IDs are unique and not overwritten. TTL is limited to 30 days. Costs must be finite and within the configured hard maximum. High-impact authorization is exact-permission scoped and cannot be implied by an ordinary grant.

## Critical enforcement boundary

The registry and evaluation API are a foundation for a central Policy Gate; they do **not** automatically grant OS, GitHub, n8n, Windows, Termux, or VPS privileges. Every execution controller must call the policy gate immediately before the side effect, using a trusted identity, exact target, exact permission, and estimated cost. Until those integrations are completed and verified, do not treat a grant as production-wide authority, and do not enable automatic destructive operations, external publication, permission changes, or paid services solely because a grant exists.

## Verification

Unit and API tests cover multi-permission grants, exact target matching, expiry, revocation persistence, wildcard denial, high-impact separation, API authentication, and UI serving. Passing these tests does not establish end-to-end enforcement by all controllers.