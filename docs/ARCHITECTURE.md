# Architecture

## Runtime flow

```text
Browser
  │  same-origin HTTP + optional Bearer token
  ▼
FastAPI (`creator_app/api.py`)
  ├── validation / size limit / rate limit / security headers
  ├── CreatorService
  │     ├── Creator Agent Catalog
  │     ├── Demo Runtime, or
  │     └── OpenAI Agents SDK → OpenAI API
  ├── Optional Codex Bridge
  │     └── Codex CLI → fixed trusted workspace
  └── SQLite
        ├── creator_runs (product history)
        └── agent_sessions / agent_messages (SDK memory)
```

## Key design choices

- **Direct specialist selection:** the menu determines the agent. This prevents an extra routing call, lowers latency/cost, and matches the product promise.
- **Local-first storage:** SQLite requires no separate database service for an individual creator.
- **One database file:** product history and Agents SDK sessions use separate tables in the same file.
- **Provider isolation:** the web UI never receives `OPENAI_API_KEY`; only the server-side runtime reads it from environment configuration.
- **Safe display:** model output is rendered as text, not injected as HTML.
- **Explicit engineering boundary:** Codex is disabled by default, requires the server bearer token,
  and uses `read-only` unless the operator deliberately enables `workspace-write`.
- **No automatic publication:** v0.2.0 has no tool that publishes content to an external service.

## Deployment boundary

The default host is `127.0.0.1`. For LAN or public hosting:

1. Set a strong `CKNEXUS_ACCESS_TOKEN`.
2. Run behind a maintained HTTPS reverse proxy.
3. Limit network exposure and back up the SQLite file.
4. Use one application worker, or migrate rate limiting and persistence to shared services before horizontal scaling.

## Deferred architecture

- Telegram adapter
- File ingestion and knowledge search
- Multi-agent handoffs and workflows
- Background jobs
- PostgreSQL
- Customer portal and SaaS billing
- Distributed rate limiting and cluster support
