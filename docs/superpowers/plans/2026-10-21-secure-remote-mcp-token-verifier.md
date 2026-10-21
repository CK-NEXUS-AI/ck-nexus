# Secure Remote MCP Token Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a provider-neutral, production-grade JWT/JWKS `TokenVerifier` for the CK-NEXUS secure Remote MCP boundary, integrate it without weakening the existing attestation/scope policy, and prove it with deterministic TDD plus runtime verification.

**Architecture:** A new deployment verifier implements the MCP SDK `TokenVerifier` interface and converts a bearer JWT into `AccessToken` only after strict signature, issuer, audience/resource, `exp`, and `iat` validation. Existing `AttestedTokenVerifier` remains the exact-resource/short-TTL/attestation boundary; MCP middleware remains authoritative for `cknexus:read` and 401/403 semantics. Runtime configuration is explicit and fail-closed; no OAuth server or token minting is added.

**Tech Stack:** Python 3, MCP SDK `mcp>=1.13,<2`, PyJWT with cryptography, `httpx`, pytest/pytest-asyncio, systemd environment configuration.

**Spec:** `docs/superpowers/specs/2026-10-21-secure-remote-mcp-token-verifier-design.md`

## Global Constraints

- Keep Remote MCP loopback-only until real verifier and edge canaries pass.
- `validate_token_resource=True` remains mandatory.
- Required scope remains exactly `cknexus:read`.
- Maximum token lifetime remains 15 minutes.
- Verify JWT signature with an explicit asymmetric algorithm allow-list; never infer security policy from the token `alg` header.
- Validate exact issuer, resource/audience, expiry, issued-at, and key identity; fail closed on ambiguity/provider failure.
- JWKS retrieval uses HTTPS, bounded timeouts, bounded response size, cache, and one refresh on unknown `kid`.
- Never log bearer tokens, Authorization headers, private keys, or raw credential-bearing claims.
- Do not mint, refresh, or manage OAuth credentials in CK-NEXUS.
- Do not expose a public listener, add write/system-exec tools, promote Q10/Q11/Q12, merge PR #14, or alter unrelated user changes.
- Preserve pre-existing `pyproject.toml` modification and `pyproject.toml.bak-mcp-20261021`.

## Review Focus

1. Algorithm confusion / `none` / symmetric-key acceptance — explicit asymmetric algorithm tests.
2. Issuer/resource confusion — exact issuer and audience/resource mismatch tests.
3. Key rotation/JWKS outage — cache, unknown-`kid` refresh, bounded failure, fail-closed tests.
4. Time-claim abuse — missing/expired `exp`, future/invalid `iat`, lifetime over 15 minutes.
5. Credential leakage — diagnostics/logs never contain bearer token or Authorization header.

---

### Task 1: Add provider-neutral JWT/JWKS verifier

**Files:**
- Create: `creator_app/device_bridge/jwt_jwks_verifier.py`
- Test: `tests/test_device_bridge_jwt_jwks_verifier.py`

**Interfaces:**
- Consumes MCP `TokenVerifier`/`AccessToken`, PyJWT, and an `httpx.AsyncClient`-compatible transport.
- Produces `JwtJwksVerifierConfig` and `JwtJwksTokenVerifier(TokenVerifier)` with `async def verify_token(token: str) -> AccessToken | None`.

- [ ] Write failing config tests for issuer/JWKS URLs, expected resource, explicit asymmetric algorithms, bounded timeout/cache values.
- [ ] Run focused tests and verify intended failure.
- [ ] Implement immutable config validation: HTTPS URLs, exact resource, non-empty allow-list, bounded timeouts/cache, no permissive defaults.
- [ ] Write failing token tests: valid JWT, malformed JWT, bad signature, unsupported algorithm, missing/unknown `kid`, wrong issuer/resource, missing/expired `exp`, invalid/future `iat`, lifetime >15 minutes.
- [ ] Run focused tests and verify intended failures.
- [ ] Implement explicit PyJWT signature/claim validation and conversion to sanitized MCP `AccessToken`.
- [ ] Implement JWKS cache, bounded HTTPS fetch, response-size bound, and one refresh on unknown `kid`; all ambiguity/network/parse errors fail closed.
- [ ] Add non-disclosure tests proving token material is absent from diagnostics.
- [ ] Run the focused suite to green.
- [ ] Commit verifier + tests only.

### Task 2: Integrate the real verifier into Remote MCP assembly

**Files:**
- Modify: `creator_app/device_bridge/remote_contract.py`
- Modify: `creator_app/device_bridge/mcp_server_v2.py` only if the injection boundary needs a minimal hook.
- Test: `tests/test_device_bridge_remote_contract.py`
- Test: `tests/test_device_bridge_remote_http_canary.py`

**Interfaces:**
- Consumes `JwtJwksTokenVerifier`, validated `RemoteBridgeConfig`, and `RemoteAttestationIdentity`.
- Produces the existing `build_remote_server(..., token_verifier=...)` boundary with the same six-tool read-only registry.

- [ ] Write a failing integration test proving missing verifier configuration is rejected and a real verifier can be injected.
- [ ] Run focused test and confirm failure.
- [ ] Implement the smallest integration change; retain `AttestedTokenVerifier` and MCP scope middleware.
- [ ] Extend canary coverage for invalid/unknown JWT => 401, valid token without scope => 403, and valid fully compliant token => successful initialize.
- [ ] Run existing remote contract + HTTP canary suites; preserve all prior checks.
- [ ] Run `compileall` for the touched package.
- [ ] Commit integration separately.

### Task 3: Add explicit runtime configuration and fail-closed startup

**Files:**
- Create/modify: `creator_app/device_bridge/remote_runtime.py` only if a focused factory is needed; otherwise use the existing service entry point.
- Modify: existing Remote MCP systemd unit/config only after inspection.
- Test: `tests/test_device_bridge_remote_runtime.py` if a runtime factory is introduced.

**Interfaces:**
- Consumes issuer URL, JWKS URL, resource URL, algorithm allow-list, timeout/cache policy from explicit deployment configuration.
- Produces a configured verifier or startup failure; never a permissive default.

- [ ] Inspect current Remote MCP systemd unit and environment source without printing secrets.
- [ ] Write failing startup tests for missing/invalid verifier configuration.
- [ ] Implement explicit environment parsing and fail-closed startup.
- [ ] Verify logs expose only bounded configuration errors, never credentials.
- [ ] Keep bind address `127.0.0.1` until edge authorization is proven.
- [ ] Commit runtime wiring separately.

### Task 4: Verify against a real authorization server

**Files:**
- No production changes unless interoperability exposes a standards defect.
- Add/update `tests/integration/test_device_bridge_real_oidc.py` only when a real provider is securely configured.
- Add/update provider-neutral deployment documentation under `docs/integrations/`.

**Interfaces:**
- Consumes authorized deployment's real issuer, JWKS endpoint, resource/audience, and short-lived test token.
- Produces sanitized evidence for `TOKEN_VERIFIER_VERIFIED`; never stores credentials.

- [ ] Check that a real issuer/JWKS configuration exists without printing secrets.
- [ ] Obtain a short-lived test token through the provider's normal mechanism; CK-NEXUS must not mint it.
- [ ] Verify cryptographic signature, exact issuer/resource, time claims, and attestation.
- [ ] Exercise expired, wrong-resource, insufficient-scope, and unknown-key negatives.
- [ ] Record only sanitized evidence IDs/timestamps.
- [ ] If no authorized provider exists, mark gate `PENDING_EXTERNAL_PROVIDER`; never fabricate success.

### Task 5: Secure-tunnel canary and final read-only verification

**Files:**
- Modify edge/tunnel configuration only after Task 4 passes.
- Test: existing `tests/test_device_bridge_remote_http_canary.py` plus tunnel-specific automation if supported.
- Documentation: update the remote MCP promotion/evidence documentation with sanitized results.

**Interfaces:**
- Consumes the verified deployment verifier and authorized edge policy.
- Produces `SECURE_TUNNEL_CANARY`, then `GPT_READ_ONLY_CANARY` only when every gate is green.

- [ ] Keep public exposure disabled until Task 4 is green.
- [ ] Verify HTTPS, exact `/mcp`, Host/Origin policy, body limit, timeout/rate-limit behavior, and 401/403 semantics at the edge.
- [ ] Verify exactly six read-only tools and no write/system-exec/production mutation through the tunnel.
- [ ] Verify sanitized audit/evidence IDs and absence of credential leakage.
- [ ] Run complete relevant tests, service health checks, and `compileall`.
- [ ] Update promotion state only from actual evidence.
- [ ] Commit documentation/evidence separately; do not auto-merge or auto-push unrelated work.

## Rollback

- Revert only verifier/integration/runtime commits created by this plan.
- Leave the pre-existing `pyproject.toml` modification and backup untouched.
- Restore Remote MCP to loopback-only if verification fails; never fall back to an unauthenticated public verifier.
- JWKS/provider failure remains fail-closed and non-public.
