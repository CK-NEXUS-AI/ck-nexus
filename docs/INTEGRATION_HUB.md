# CK-NEXUS Integration Hub — R14

CK-NEXUS owns orchestration and execution policy. Integrations are adapters behind the
Capability/Skill layer; no external workflow engine is part of the runtime path.

## Active server-side integrations

- GitHub — token/GitHub App through Credential Broker and integration adapter.
- Slack — server credential through trusted-host HTTPS adapter.
- Google Drive — server OAuth/access token through trusted-host HTTPS adapter.
- Gmail — OAuth credentials through Credential Broker.
- OpenAI — provider credential through Credential Broker; live connectivity remains AI001.
- PostgreSQL/SQLite — canonical application and email state.
- Redis/PostgreSQL idempotency adapters — optional distributed execution coordination.

## Retired integration

n8n was removed from the active CK-NEXUS runtime in R14. Historical R4-R13 documents may
mention n8n as evidence of earlier architecture, but no current compose service, API integration,
P0 gate, or deployment script may start or require it.

## Security rule

Secrets are server-side only. Status APIs return configuration/health metadata and never return
secret values. All mutations remain subject to CK-NEXUS permissions, idempotency, evidence and
verification gates.
