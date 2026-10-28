# CK-NEXUS Remote MCP Connection Readiness

Date: 2026-10-26

## Verified current state

- `cknexus-mcp.service` is active and binds to `127.0.0.1:8765`.
- The deployed server implements Streamable HTTP at `/mcp` and explicitly documents itself as loopback-only.
- The service unit runs as `cknexus-agent` with `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, and a restricted writable path.
- A local unauthenticated GET to `/mcp` returned HTTP 406 because it was not an MCP client initialization request. This is not proof of remote authentication or tool authorization.
- Local checks found `/health` on ports 8787 and 8790, but `/mcp` returned 404 on those ports. No existing MCP gateway route was verified.
- The example URL `https://my-mcp-server.ai/mcp` is a placeholder, not a verified CK-NEXUS endpoint. The n8n domain `xtzsfd91.rpcld.co` is a different application and must not be reused as an MCP endpoint without an explicitly configured route.

## Connection decision

Do not configure a public Remote MCP client yet. The current MCP service is intentionally loopback-only and no authenticated HTTPS `/mcp` boundary has been verified. Do not expose port 8765 directly, set Authentication to `None`, or enable every tool by default.

## Required implementation before remote connection

1. Choose a controlled public hostname and TLS termination point.
2. Add an authenticated reverse-proxy or MCP gateway route for `/mcp`; do not forward the raw loopback service to the public internet.
3. Require and validate Bearer/OAuth credentials for every protected request, including audience/resource binding when using OAuth. Never place tokens in URLs, source code, logs, or task evidence.
4. Add per-tool authorization and start with read-only tools only. Keep enqueue/worker or other state-changing tools disabled until their scopes and approval policy are reviewed.
5. Apply rate limits, request-size limits, timeouts, Origin/Host validation where applicable, and audit logging with secrets redacted.
6. Test the remote endpoint with no token (must reject), invalid/expired token (must reject), valid least-privilege token (must list only authorized tools), and one harmless read-only tool call.
7. Record the verified URL, authentication method, tool allowlist, test outputs, and rollback procedure. Only then configure the client.

## Safe client configuration target

- Name: `CK-NEXUS`
- URL: the actual verified HTTPS hostname ending in `/mcp` (not the example URL)
- Transport: Streamable HTTP
- Authentication: Bearer/OAuth supported by the deployed gateway
- Tools: explicit allowlist of read-only status/inventory tools; do not select `All` by default

## Status

`BLOCKED_ON_AUTHENTICATED_HTTPS_BOUNDARY`. No public MCP endpoint was configured or exposed during this audit.
