# R14 — Cognitive Brain Runtime + n8n Retirement

## Goals

1. Make OpenAI the primary cognitive provider without installing credentials as process-global defaults.
2. Keep CK-NEXUS as authority for state, permissions, credentials, tools and verification.
3. Remove n8n from the active runtime/deployment path.
4. Preserve historical lineage and fail-closed production posture.

## OpenAI runtime

- OpenAI Agents SDK is configured per run with `OpenAIProvider(api_key=..., use_responses=True)`.
- The API key comes from Credential Broker and is never copied into source/config responses.
- Tracing is disabled by default. If explicitly enabled, the tracing credential is scoped to the run.
- `OPENAI_MODEL` defaults to `gpt-5.6-sol` and remains fully overridable.
- Creator Runtime and Development Council share the same per-run brain configuration.

## n8n retirement

Removed from:

- Integration Hub runtime and UI.
- Production/P0 compose services and environment variables.
- VPS bring-up and security gate.
- P0 email routing gate (replaced by direct CK-NEXUS Email Gateway routing verification).

Historical documents remain untouched as lineage evidence and must not be interpreted as current architecture.

## Remaining production gates

- Live OpenAI AI001 with an account-authorized model.
- Live PostgreSQL/Redis distributed idempotency evidence.
- cgroup v2 enforcement on a delegated Linux host.
- Security tooling (`gitleaks`, `bandit`, `pip-audit`) in a fully provisioned build environment.
- Backup/restore, observability and clean-machine staging evidence.
