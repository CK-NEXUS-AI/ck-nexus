# Secure Remote MCP Contract V1

Status: development/security hardening only. No public endpoint is deployed by this change.

## Goal

Expose the CK-NEXUS clean-room MCP registry remotely without changing authority, tool scope, or the
quarantine status of `gptos.intelligence.assistant`.

```text
CK-NEXUS clean-room MCP
  -> loopback-only Streamable HTTP
  -> authenticated secure tunnel / reverse proxy
  -> public HTTPS /mcp
  -> OAuth protected resource
  -> GPT/OpenAI remote MCP client
```

## Enforced contract

The remote resource requires HTTPS, exact `/mcp`, no URL userinfo/query/fragment, public resource and
issuer identities, `cknexus:read`, loopback bind intent, a non-privileged port, an injected real
`TokenVerifier`, exact source/tree/registry/descriptor attestation, and access-token lifetime of at
most 15 minutes. Remote HTTP is explicitly stateless and its request body is capped at 64 KiB.

The module does not mint tokens, store credentials, configure DNS, create a tunnel, or deploy a public
endpoint. The exact six read-only MCP tools remain unchanged.

## Authentication versus authorization

The deployment verifier performs cryptographic verification or standards-based token introspection.
`AttestedTokenVerifier` then verifies client identity, exact resource, issuer, expiry, issued-at, short
lifetime, and exact CK-NEXUS attestation. It intentionally does **not** reject an otherwise authentic
token merely because `cknexus:read` is missing. The MCP SDK's required-scope middleware owns that
authorization decision so semantics remain:

- missing or invalid authentication -> HTTP 401
- authenticated token with insufficient scope -> HTTP 403
- authenticated exact token with `cknexus:read` -> eligible for the read-only MCP registry

Raw access tokens must never be written to logs, evidence, GitHub, or memory.

## Attestation claim

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

## Local HTTP canary

The development canary uses the SDK's in-process ASGI application; it does not open a socket. Tests
prove the intended boundary before any tunnel exists:

1. no Authorization header -> 401
2. invalid token -> 401
3. valid identity lacking `cknexus:read` -> 403
4. exact authenticated initialize request -> 200
5. invalid Host -> 421
6. invalid Origin -> 403
7. request larger than 64 KiB -> 413
8. registry remains exactly six tools with read-only, non-destructive, idempotent, closed-world hints

The loopback host also causes the MCP SDK to enable its transport-security Host/Origin allowlist for
localhost. This local proof does not prove the future public DNS/tunnel configuration.

## Remaining remote gates

Before a secure-tunnel canary: verify real authorization-server integration, runtime DNS/Host/Origin
policy at the edge, output limits, request timeout, rate limiting, sanitized audit/evidence IDs, token
revocation behavior, and no credential leakage. Bearer replay remains a residual risk during the short
token lifetime, so V1 remains read-only; DPoP or mTLS can only be considered later if supported end to
end by the chosen client and authorization provider.

Promotion remains:

`CONTRACT_ONLY -> LOCAL_AUTH_CANARY -> TOKEN_VERIFIER_VERIFIED -> SECURE_TUNNEL_CANARY -> GPT_READ_ONLY_CANARY -> GOVERNANCE_REVIEW`

Q10/Q11/Q12 and production closure status are unchanged.
