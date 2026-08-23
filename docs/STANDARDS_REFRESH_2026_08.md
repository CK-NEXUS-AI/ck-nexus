# CK-NEXUS Standards Refresh — 2026-08

Status: DEVELOPMENT / NOT INDEPENDENTLY VERIFIED

This refresh is Delta-only and does not change production closure authority.

## Corrected current facts

- MCP latest specification: `2026-07-28`.
  - Stateless request/response core.
  - No mandatory session/handshake affinity assumption.
  - Header-aware routing and cacheable list results.
  - Tasks, MCP Apps and other capabilities are extensions.
  - Authorization was hardened and protocol deprecation is formalized.
- A2A latest released version: `1.0.0`.
  - Agent Card, task/message/artifact interoperability remains separate from CK execution authority.
  - Compatibility/TCK evidence must not be treated as trust or permission evidence.
- Microsoft Agent Framework is the active successor path combining AutoGen/Semantic Kernel concepts.
- OpenAI Agents SDK now exposes tool guardrails for function tools and resumable sandbox-agent sessions.
  - Native guardrail coverage is not universal across hosted tools, handoffs, built-in computer/shell/apply-patch tools, or agents-as-tools.
  - CK-NEXUS Governor must remain the independent pre-execution boundary.
- OWASP Top 10 for Agentic Applications 2026 is current.
- OWASP GenAI LLM Top 10 2026 is current.
- NIST AI 600-1 remains the published Generative AI Profile.
- NIST Cyber AI Profile work is still in development; do not make final-compliance claims against it.
- OpenTelemetry GenAI semantic conventions now include tool definitions/types and cache token attributes; CK should map telemetry without recording raw secrets/prompts by default.

## New deltas added

1. Protocol version authority registry.
2. Explicit MCP/A2A compatibility state.
3. Tool guardrail coverage matrix that fails closed to CK Governor.
4. Privacy-minimal OpenTelemetry GenAI semantic mapping.
5. Freshness-aware standards baseline to prevent stale compliance/design claims.

## Claim rules

- CI PASS != VERIFIED.
- TCK/compatibility PASS != execution trust.
- Protocol compatibility != permission grant.
- Standard mapping != compliance certification.
- Development implementation != production readiness.

## Next verification

Run unit/static tests, capture evidence, then obtain independent verification before changing any capability claim to VERIFIED.
