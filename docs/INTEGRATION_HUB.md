# CK-NEXUS Integration Hub — R4

Status: **Release Candidate**. This feature does not close P0 production runtime gates by itself.

## Supported status checks

- GitHub — `GITHUB_TOKEN`, `GITHUB_REPO`, `GITHUB_API_BASE`
- Slack — `SLACK_BOT_TOKEN`, optional `SLACK_API_BASE`
- Google Drive — `GOOGLE_DRIVE_ACCESS_TOKEN`, optional `GOOGLE_DRIVE_API_BASE`
- n8n — `N8N_BASE_URL`, `N8N_API_KEY`
- OpenAI — `OPENAI_API_KEY` presence + selected `OPENAI_MODEL`; live AI connectivity remains AI001
- Database — local SQLite or configured PostgreSQL reachability

## API

- `GET /api/integrations/status`
- `POST /api/integrations/test-all`
- `GET /api/integrations/github/status`
- `POST /api/integrations/github/test`

When `CKNEXUS_ACCESS_TOKEN` is configured, integration endpoints require the same Bearer token.

No integration endpoint returns secret values.

## Credential boundary

ChatGPT connector credentials are not exported into CK-NEXUS. Runtime credentials must be configured independently on the server/VPS through environment variables or a secret manager.

## OpenAI model default

R4 uses `gpt-5-mini` as the default API model while preserving `OPENAI_MODEL` override. Confirm account availability before production deployment.

## n8n

CK-NEXUS verifies n8n through the Public API using `X-N8N-API-KEY`. The n8n security audit remains a separate P0 security gate and must be executed against the actual staging/production instance.
