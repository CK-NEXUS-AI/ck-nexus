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
- explicit localhost/private IP literals are rejected as public resource/issuer identities
- no username/password, query string, or fragment in configured URLs
- only `cknexus:read` scope
- local MCP bind host remains loopback (`127.0.0.1`, `localhost`, or `::1`)
- non-privileged local port
- a real MCP `TokenVerifier` supplied by the deployment integration
- the same six read-only tools as the local clean-room MCP server
- token binding to exact source commit, source tree, registry SHA-256, and descriptor SHA-256
- a short token lifetime of at most 15 minutes

The module does not mint tokens, store credentials, open a listener, configure DNS, or deploy a
public endpoint.

## Authorization boundary

For Streamable HTTP, CK-NEXUS treats the MCP server as an OAuth resource server. The authorization
server is separate and must issue access tokens for this MCP resource. The MCP server validates every
bearer token and required scope before tool execution.

`AttestedTokenVerifier` wraps the deployment verifier. The deployment verifier remains responsible for
cryptographic verification or standards-based token introspection. The wrapper then additionally
requires:

- non-empty client identity
- `cknexus:read` scope
- exact resource/audience match to the configured public `/mcp` URL
- non-expired access token
- issuer claim match
- issued-at claim and maximum 15-minute lifetime
- exact `cknexus_attestation` claim containing source commit/tree and registry/descriptor digests

Raw access tokens must never be written to logs, evidence, GitHub, or memory.

## Attestation claim

The authorization integration must mint an attestation claim only after a clean local attestation:

```json
{
  "cknexus_attestation": {
    "source_commit": "<40 hex>",
    "source_tree": "<40 hex>",
    "registry_sha256": "<64 hex>",
    "descriptor_sha256": "<64 hex>"
  }
}
```

A token for a stale build, changed registry, or changed descriptor fails closed.

## Network boundary

The MCP process remains loopback-only. Remote reachability belongs to an authenticated tunnel or
reverse proxy with TLS and strict Host/Origin policy. Do not bind the MCP server directly to
`0.0.0.0` and do not expose an unauthenticated HTTP wrapper.

The public hostname still requires runtime DNS/Host/Origin verification. Static configuration checks
cannot prove that a DNS name will never resolve to a private address, so DNS-rebinding protection
remains a deployment/canary gate.

## Replay model and residual risk

V1 uses OAuth bearer tokens. TLS, exact audience/resource binding, exact attestation binding, and a
short lifetime reduce replay exposure, but a stolen bearer token can still be replayed within its
valid lifetime. V1 therefore remains read-only and must not be promoted to mutation authority.
Proof-of-possession such as DPoP or mTLS may be considered later only if the selected remote client
and authorization provider support it end to end.

## Remote canary gates

Before remote canary promotion, independently verify:

1. exact source commit/tree and clean checkout
2. exact six-tool registry and read-only annotations
3. unauthenticated `/mcp` returns 401 before tool parsing/execution
4. invalid, expired, wrong-issuer, wrong-resource, or stale-attestation tokens return 401
5. insufficient scope returns 403
6. valid read-only token can list/call only the six allowed tools
7. DNS-rebinding/Host/Origin protections reject unapproved values
8. request/output size, timeout, and rate limits are enforced at the remote boundary
9. no credentials appear in responses/logs/evidence
10. Android AnyClaw remains quarantined and no production mutation is possible

## Promotion state

`CONTRACT_ONLY -> TOKEN_VERIFIER_VERIFIED -> LOCAL_AUTH_CANARY -> SECURE_TUNNEL_CANARY -> GPT_READ_ONLY_CANARY -> GOVERNANCE_REVIEW`

Q10/Q11/Q12 and production closure status are unchanged.
