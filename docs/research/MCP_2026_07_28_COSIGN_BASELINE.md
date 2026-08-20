# CK-NEXUS Research Baseline — MCP 2026-07-28 + Cosign 3.1.3

Status: **LOCAL_EVALUATE / NOT_PRODUCTION_EVIDENCE**

This research slice is intentionally isolated from the production-closure lineage. It does not
promote Q10, Q11, or Q12, does not merge PR #14, does not deploy a public MCP endpoint, and does not
sign or verify artifacts against external services.

## Current canonical context

The current canonical `main` already contains a read-only clean-room MCP server plus a secure remote
contract. The remote HTTP canary is loopback-only and explicitly stateless, but the existing canary
still exercises the legacy `initialize` handshake and protocol version `2025-11-25`.

Therefore the 2026-07-28 work is a **migration delta**, not a second MCP authority.

## MCP 2026-07-28 migration contract

`creator_app/device_bridge/mcp_2026_07_28.py` models the new stateless gateway boundary without
opening a listener or executing tools.

V1 research invariants:

- protocol target is `2026-07-28`;
- protocol-level session headers are denied;
- `initialize` and `notifications/initialized` are denied as legacy handshake methods;
- gateway routing uses `Mcp-Method` and optional `Mcp-Name`;
- per-request capabilities are self-contained request metadata and must be unique/bounded;
- stdio and Streamable HTTP remain the only accepted migration transports;
- legacy SSE is denied;
- list requests may derive deterministic cache keys only when not task-scoped;
- evidence stores request-parameter digests rather than raw parameter payloads.

This module does **not** claim that the currently locked upstream MCP Python SDK already implements
the complete 2026-07-28 wire protocol. Wiring it into the live server requires an explicit
compatibility decision and targeted SDK verification first.

### Minimum compatibility harness before activation

1. A request reaches the adapter without a protocol session.
2. A legacy `initialize` request is rejected.
3. `Mcp-Method`/`Mcp-Name` routing metadata is exact and mismatch fails closed.
4. Per-request capabilities do not persist across calls.
5. Cache identity for list requests is deterministic and does not contain raw payloads.
6. Tasks/MRTR behaviors are tested against the official SDK only after exact method/capability
   semantics are verified from upstream documentation.
7. OAuth/resource/issuer/attestation checks from the existing remote contract remain authoritative.

## Cosign security baseline

`creator_app/supply_chain_cosign.py` is a pre-execution policy gate. It does not invoke Cosign.

CK-NEXUS research policy V1:

- approved major: `3`;
- minimum approved version: `3.1.3`;
- `3.1.2` and lower are rejected;
- v2 is not admitted into this CK-NEXUS baseline even if an upstream v2 patch exists;
- future major versions are rejected until reviewed;
- standardized bundles only;
- legacy JSON or unknown bundle formats are denied;
- artifact SHA-256, certificate identity, and HTTPS OIDC issuer are required before execution;
- evidence stores digests of identity/issuer instead of copying them verbatim.

### Required negative test before a real signing/verification PoC

A fixture classified as a legacy JSON bundle must fail policy validation before any verifier
execution is permitted. A later executable canary must additionally prove that the pinned Cosign
binary rejects the advisory-class legacy bypass case while enforcing certificate identity and OIDC
issuer policy.

## Explicit non-goals

- no package installation;
- no Sigstore transparency-log call;
- no remote MCP connection;
- no credential minting or persistence;
- no prompt/tool argument capture for telemetry;
- no production deployment;
- no release-gate promotion.

## Next research slices

After this branch passes exact-head CI:

1. verify upstream MCP SDK compatibility with 2026-07-28 and implement a loopback-only canary;
2. add an executable Cosign `>=3.1.3` local canary using fixture artifacts only;
3. Temporal crash/retry/resume PoC;
4. OpenTelemetry GenAI schema mapping with content capture disabled by default;
5. Netdata MCP read-only local observability evaluation;
6. OPA deterministic decision evidence;
7. A2A signed Agent Card trust-root interoperability;
8. Playwright MCP vs CLI+Skill benchmark.

Production status remains **NO-GO** until the authoritative production gates close independently.
