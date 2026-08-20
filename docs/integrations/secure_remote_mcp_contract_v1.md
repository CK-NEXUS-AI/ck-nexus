# Secure Remote MCP Contract V1

Status: development/security hardening only. No public endpoint is deployed by this change.

## Goal

Expose the CK-NEXUS clean-room MCP registry remotely without changing authority, tool scope, or the
quarantine status of `gptos.intelligence.assistant`.

The intended shape is:

```text
CK-NEXUS clean-room MCP
  -> bind 127.0.0.1 only
  -> authenticated secure tunnel / reverse proxy
  -> public HTTPS /mcp
  -> OAuth 2.1 bearer-token protected resource server
  -> GPT/OpenAI remote MCP client
```

## Enforced contract

`creator_app.device_bridge.remote_contract` requires:

- public MCP resource URL uses HTTPS and exact `/mcp` path
- authorization issuer uses HTTPS
- no username/password, query string, or fragment in configured URLs
- only `cknexus:read` scope
- local MCP bind host remains loopback (`127.0.0.1`, `localhost`, or `::1`)
- non-privileged local port
- a real MCP `TokenVerifier` supplied by the deployment integration
- the same six read-only tools as the local clean-room MCP server

The module does not mint tokens, store credentials, open a listener, configure DNS, or deploy a
public endpoint.

## Authorization boundary

For Streamable HTTP, CK-NEXUS treats the MCP server as an OAuth resource server. The authorization
server is separate and must issue access tokens for this MCP resource. The MCP server validates every
bearer token and required scope before tool execution.

The eventual verifier should validate token issuer, intended audience/resource, expiry, subject/client
identity, and `cknexus:read` scope. Raw access tokens must never be written to logs, evidence, GitHub,
or memory.

## Network boundary

The MCP process remains loopback-only. Remote reachability belongs to an authenticated tunnel or
reverse proxy with TLS and strict host/origin policy. Do not bind the MCP server directly to
`0.0.0.0` and do not expose an unauthenticated HTTP wrapper.

Before remote canary promotion, independently verify:

1. exact source commit/tree and clean checkout
2. exact six-tool registry and read-only annotations
3. unauthenticated `/mcp` returns 401 before tool parsing/execution
4. invalid/expired/wrong-audience tokens return 401
5. insufficient scope returns 403
6. valid read-only token can list/call only the six allowed tools
7. DNS-rebinding/Host/Origin protections reject unapproved values
8. no credentials appear in responses/logs/evidence
9. Android AnyClaw remains quarantined
10. no production mutation is possible

## Promotion state

`CONTRACT_ONLY -> TOKEN_VERIFIER_VERIFIED -> LOCAL_AUTH_CANARY -> SECURE_TUNNEL_CANARY -> GPT_READ_ONLY_CANARY -> GOVERNANCE_REVIEW`

Q10/Q11/Q12 and production closure status are unchanged.
