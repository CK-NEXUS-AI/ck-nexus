# Secure Remote MCP Token Verifier Design

**Status:** Proposed design; implementation not yet started.

## Goal

Add a production-grade OAuth/OIDC access-token verification boundary for CK-NEXUS Remote MCP so the existing `AttestedTokenVerifier` can consume tokens verified by a real authorization-server integration, without exposing the local MCP listener or weakening the existing read-only contract.

## Scope

This design covers only the authentication boundary required to advance:

`LOCAL_AUTH_CANARY -> TOKEN_VERIFIER_VERIFIED -> SECURE_TUNNEL_CANARY`

It does not authorize a public endpoint, create DNS, create a tunnel, mint credentials, change the six-tool MCP registry, enable mutation tools, or alter Q10/Q11/Q12 governance state.

## Current Constraints

- Remote MCP remains loopback-only until a real verifier and edge controls are independently verified.
- `build_remote_server()` must continue to receive a real `TokenVerifier`; no static/fake verifier may be used outside tests.
- `AuthSettings.validate_token_resource` remains enabled.
- Required scope remains exactly `cknexus:read` and scope authorization remains owned by MCP middleware.
- `AttestedTokenVerifier` remains the CK-NEXUS policy layer for resource, issuer, expiry, issued-at, token lifetime, and exact build attestation.
- Access tokens, refresh tokens, private keys, and authorization headers must never be logged, committed, or written to evidence.
- Token lifetime remains capped at 15 minutes by the CK-NEXUS policy layer.
- Verification failures are fail-closed.

## Recommended Architecture

Use a small provider-neutral JWT/JWKS verifier implemented with the already-present `PyJWT[crypto]`, `cryptography`, and `httpx` dependencies. The verifier receives an issuer URL, JWKS URL, expected audience/resource, and bounded HTTP/cache settings from runtime configuration. It fetches public signing keys over HTTPS, caches them for a bounded period, selects the key by JWT `kid`, verifies the signature and standard claims, and returns the MCP SDK `AccessToken` only after all provider-independent checks pass.

The resulting chain is:

```text
Bearer token
  -> deployment TokenVerifier
  -> JWT signature + issuer/audience/exp/iat checks
  -> AccessToken
  -> AttestedTokenVerifier
  -> exact resource + TTL + CK-NEXUS attestation
  -> MCP required-scope authorization
  -> six read-only tools
```

The provider-specific issuer/JWKS values are configuration, not hard-coded source. The implementation must not guess or silently discover an authorization provider. A real provider must be configured before the verifier can be promoted to production use.

## Components

### 1. Production JWT/JWKS verifier

Create a focused module under `creator_app/device_bridge/` responsible only for external token verification.

Required interface:

```python
class JwtJwksTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None: ...
```

Configuration must include:

- issuer URL
- JWKS URL
- expected resource/audience
- allowed signing algorithms, explicitly configured and never inferred from the token header
- JWKS cache lifetime
- HTTP connect/read timeout

The verifier must reject malformed tokens, unsupported algorithms, invalid signatures, unknown `kid`, wrong issuer, wrong audience/resource, missing/invalid expiry, and tokens outside the accepted issued-at policy.

JWKS retrieval must use HTTPS, bounded timeouts, bounded response size, and no credential-bearing requests. Key refresh on an unknown `kid` may perform one bounded re-fetch; repeated failure returns `None`.

### 2. Runtime configuration

Add explicit configuration for the verifier without storing secrets in source control. The preferred deployment input is environment/systemd secret configuration because the verifier needs public metadata rather than a client secret.

The configuration must fail closed when required issuer/JWKS/resource values are absent or malformed. No default public authorization provider may be assumed.

### 3. Existing attestation layer

Keep `AttestedTokenVerifier` unchanged except where tests demonstrate a necessary integration mismatch. Its existing checks remain authoritative for CK-NEXUS identity and build attestation.

### 4. Remote MCP assembly

`build_remote_server()` continues to wrap the deployment verifier with `AttestedTokenVerifier` and keeps the local listener loopback-bound. No public bind change is part of this design.

## Authentication Semantics

- No bearer token -> HTTP 401 through MCP authentication middleware.
- Invalid signature/issuer/audience/expiry -> HTTP 401.
- Valid token but missing `cknexus:read` -> HTTP 403 through MCP authorization middleware.
- Valid token with correct scope but stale/wrong CK-NEXUS attestation -> authentication failure according to the existing middleware boundary; it must never reach a tool.
- Correct token, resource, issuer, TTL, attestation, and scope -> eligible for the existing six read-only tools.

## Security Requirements

1. Never accept `alg` solely because it appears in the JWT header.
2. Never accept `none` or symmetric algorithms unless explicitly and intentionally configured; the initial implementation should allow only the configured asymmetric algorithm set.
3. Validate `iss`, `aud`/resource, `exp`, and `iat` before returning an `AccessToken`.
4. Enforce bounded JWKS HTTP timeouts and response size.
5. Cache public keys with a bounded lifetime and refresh once for an unknown `kid`.
6. Do not log bearer tokens, JWTs, Authorization headers, JWKS private material, or raw authentication failures containing credentials.
7. Preserve the existing 15-minute CK-NEXUS token lifetime policy in `AttestedTokenVerifier`.
8. Fail closed if JWKS cannot be retrieved or validated.
9. Keep Remote MCP loopback-only until the verifier canary passes and a separate edge/tunnel canary is completed.
10. Do not implement token minting, refresh-token handling, or credential rotation in this component.

## Testing Strategy

TDD is required for implementation.

Unit tests must cover at least:

- valid signed token
- invalid signature
- malformed JWT
- unsupported algorithm
- missing `kid`
- unknown `kid` with failed refresh
- successful unknown-`kid` refresh
- wrong issuer
- wrong audience/resource
- expired token
- missing expiry
- invalid issued-at
- future issued-at beyond allowed clock skew
- JWKS HTTP timeout/failure
- oversized/invalid JWKS response
- cache hit without unnecessary network fetch
- no credential/token leakage in exception/log paths

Integration/canary tests must then prove the verifier plugs into the existing `AttestedTokenVerifier` and preserves the current 14-test Remote MCP contract/canary suite.

## Promotion Gates

### TOKEN_VERIFIER_VERIFIED

Required evidence:

- real authorization-server issuer configured
- real JWKS endpoint reachable over HTTPS
- valid signed token accepted
- invalid signature rejected
- wrong issuer/resource rejected
- expired token rejected
- missing scope reaches 403 through MCP middleware
- no token/credential leakage observed in logs
- existing Remote MCP suite remains green

### SECURE_TUNNEL_CANARY

Only after the previous gate passes. The local MCP listener remains loopback-only. The external edge must enforce HTTPS, correct Host/Origin behavior, request-size/time limits, rate limiting, sanitized audit IDs, and a routing boundary to the loopback service. The public endpoint must not expose the local port directly.

### GPT_READ_ONLY_CANARY

Only after the secure tunnel canary passes. The client may exercise only the six existing read-only tools. No mutation, shell, file-write, production deployment, or merge operation is permitted through this path.

## Non-Goals

- No fake/static production verifier.
- No public MCP exposure before authentication is proven.
- No OAuth authorization-server implementation inside CK-NEXUS.
- No token minting.
- No production mutation tools.
- No agent write access.
- No automatic merge/push/deployment.

## Open Operational Input

The implementation can be provider-neutral, but promotion to `TOKEN_VERIFIER_VERIFIED` requires an actual authorization-server issuer and JWKS configuration. Those values must come from an authorized provider/deployment secret configuration; they must not be invented by the implementation.
