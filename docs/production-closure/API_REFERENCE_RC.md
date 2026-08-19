# CK-NEXUS Release Candidate API Reference

Status: evidence-backed partial reference for the frozen runtime. The running FastAPI OpenAPI schema is authoritative for the complete endpoint catalog.

## Security model

Protected application APIs use bearer authentication when `CKNEXUS_ACCESS_TOKEN` is configured. Email gateway routes use a separate CK-NEXUS webhook token. The application applies request-size protection, rate limiting on generation paths, correlation IDs and security response headers.

## Verified email gateway endpoints in the frozen source

### `POST /api/email/ingest`
Claims an inbound provider message atomically and returns accepted/duplicate status with journal identity. Requires the email webhook token and the email gateway to be enabled.

### `POST /api/email/outbox`
Enqueues a deduplicated outbound action associated with an email journal record. Requires the email webhook token.

### `POST /api/email/route`
Evaluates deterministic email routing policy and returns category, priority, matched rule and reasons.

### `POST /api/email/loop-check`
Evaluates headers for automatic-reply loop prevention.

### `POST /api/email/scan-attachment`
Scans an uploaded attachment and returns safety/status metadata, SHA-256, size, extension and detected MIME. The frozen implementation rejects attachments exceeding 25 MiB.

### `POST /api/email/outbox/claim`
Claims a batch of queued outbox items for a worker lease.

### `POST /api/email/outbox/{outbox_id}/sent`
Marks a claimed outbox item as sent and records provider-message/audit information.

## Other runtime surfaces

The frozen FastAPI application wires Creator Runtime, agent catalog/service, AGNES, provider router, dynamic connector fabric, GitHub App, Gmail OAuth, Slack, Google Drive, Codex bridge, health/observability and storage services. Endpoint availability depends on feature flags/settings and credentials.

For client generation or integration work, fetch the OpenAPI schema from the exact running frozen build rather than relying on this summary. This avoids claiming an endpoint that belongs only to development `main` or another branch.

## Error classes visible in the API layer

The API emits structured HTTP errors for unauthorized access, missing OpenAI credentials, provider runtime failures, disabled connector/Codex/email capabilities, integration errors, rate limits and oversized requests. Consumers must treat 5xx capability/configuration errors as distinct from successful execution evidence.
