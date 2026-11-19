# CK-NEXUS R7 — Credential Broker & Provider Cutover

Status: **Development Candidate / Release Candidate / NO-GO for Production claims**

Baseline: R6 Autonomy Hardening commit `4603d45acdbde13491582c7a6f85570372035c86`.

## Implemented

- Credential Broker with explicit consumer-to-secret allowlists, consumer-bound leases, redacted `repr`, redacted status, environment bootstrap, and ephemeral runtime token storage.
- Provider adapters:
  - `mock` for deterministic local demonstrations.
  - `ollama` for local text generation; base URL is restricted to explicit loopback hosts and may not contain credentials/query/fragment data.
  - `openai` using the OpenAI Responses API through a broker-provided API key.
- Provider Router cutover:
  - CreatorRuntime selects an eligible `text` provider. Ollama uses the router adapter path; OpenAI keeps Agents SDK sessions/instructions and reports success/failure back to the router circuit breaker.
  - Development Council requires an `agents-sdk` capability and therefore fails closed unless an eligible OpenAI provider is available. The Council continues to use specialist agents + orchestrator rather than pretending a single local model is the full council.
- OpenAI Agents SDK runs set `trace_include_sensitive_data=False`.
- Gmail OAuth:
  - server-side authorization code flow, one-time state, offline access, read-only scope by default, optional send scope.
  - access/refresh tokens are stored only in the in-process broker in this development slice and are never returned from API endpoints.
- GitHub App:
  - RS256 JWT signer seam; installation token minting uses exact `api.github.com`, redirects disabled, current API-version header configurable, and installation tokens stay inside the broker.
  - default JWT signer is an optional `PyJWT[crypto]` package extra.

## Security boundaries

- No bulk credential export API.
- No secret values in provider, credential, Gmail, or GitHub App status endpoints.
- Gmail OAuth callback is protected by one-time state; production still needs durable encrypted refresh-token storage.
- GitHub App token endpoint returns only safe status.
- Ollama external-host URLs are rejected before prompts are sent.
- Existing Slack/Drive/GitHub credential-bearing redirects remain blocked by the R6 integration-security layer.

## Production gates still open

- Durable encrypted credential/vault backend and key rotation policy.
- Real Gmail OAuth callback against an owned test account and revocation/refresh evidence.
- Real GitHub App installation/token refresh against the target repository.
- Live OpenAI AI001 evidence and local Ollama runtime evidence where enabled.
- PostgreSQL/email/n8n/backup/observability/clean-machine P0 gates inherited from R5/R6.

Do not label this build Production Ready until those gates pass against one immutable release identity and environment.
