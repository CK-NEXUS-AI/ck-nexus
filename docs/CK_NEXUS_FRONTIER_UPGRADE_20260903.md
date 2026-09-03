# CK-NEXUS Frontier Upgrade Plan — 2026-09-03

Status: DEVELOPMENT ONLY / MEASURED_NOT_VERIFIED
Frozen Q10 subject remains immutable. Production remains NO-GO.

## Operating rule
Search-first -> Delta-only -> Reuse/Dedup -> Benchmark -> Security review -> Independent verification -> Canonical adoption.
A candidate is rejected if it neither improves the measured baseline nor adds a required capability.

## Standards snapshot
- OWASP GenAI LLM Top 10 2026 and Agent Control Standard: current 2026 baseline.
- OWASP Top 10 for Agentic Applications 2026: current agentic-risk baseline.
- MCP target: 2026-07-28 stateless protocol core.
- A2A target: current released specification; verify exact version at implementation time.
- OpenTelemetry: GenAI semantic conventions for model/agent/tool traces.
- NIST: AI RMF 1.0 + NIST AI 600-1 GenAI Profile; track 2026 AI RMF revision work.

## Baseline matrix
| # | Priority | Capability | Current evidence | State | Next delta |
|---|---|---|---|---|---|
| 1 | P0 | Agent Security & Governance | permission, sticky approval, identity, taints, sensitive args, fail-closed | PARTIAL | untrusted-input side-effect/memory/handoff enforcement + OWASP/ACS mapping |
| 2 | P0 | MCP 2026-07-28 | stateless discovery, headers, cache metadata, tool gating | PARTIAL | conformance audit: OAuth/CIMD, issuer/audience, DNS rebinding, output schema, MRTR |
| 3 | P0 | A2A interoperability | no repo-wide implementation found | ABSENCE_NOT_PROVEN | minimal governed adapter + discovery/task contract |
| 4 | P1 | GenAI observability | generic OTel dependency only | GAP | GenAI spans/metrics with privacy-safe content defaults |
| 5 | P1 | NIST/ISO evidence mapping | no code/docs mapping found in baseline scan | GAP | machine-readable control/evidence crosswalk |
| 6 | P1 | Connector Trust Fabric | R28 connector lifecycle, risk, activation, Credential Broker | PRESENT_PARTIAL | complete authority wiring and transport/output hardening |
| 7 | P1 | Multi-model Routing V2 | provider router, fallback, circuit breaker, local-first | PARTIAL | capability/quality/latency/context/privacy/benchmark-aware scoring |
| 8 | P2 | Memory V3 | Unified Memory V2 has authority, confidence, TTL, provenance digest | PARTIAL | explicit trust/taint, conflict detection, episodic/task memory, retrieval eval |
| 9 | P2 | Long-context intelligence | no semantic chunk/rerank/context-budget implementation found | GAP | hierarchical retrieval + provenance-preserving citations |
| 10 | P2 | Eval & Regression Fabric | strong test/gate/dynamic-verifier primitives | PARTIAL | normalized before/after benchmark schema and reject-on-no-delta gate |
| 11 | P2 | Resilient execution | idempotency, replay guards, circuit breaker, durable pipeline | PRESENT_PARTIAL | checkpoint/resume + compensation contract audit |
| 12 | P3 | Multimodal Runtime | limited modality references only | PARTIAL | typed modality capabilities and per-modality permissions |

## Delta 01 — Agent Security Context
Baseline test: tests/test_r10_orchestration_canonical.py = 8/8 PASS.
Candidate adds explicit input trust, taints and trusted confirmation to ExecutionContext plus side-effect, memory-write and cross-agent-handoff markers to ToolRequest.
Guardrail denies sensitive agent actions sourced from untrusted/tainted input unless a trusted runtime supplies explicit confirmation. Existing permission, approval, circuit, credential, timeout and idempotency gates still run afterward.
Candidate regression: 13/13 PASS (existing 8 + 5 new security cases).

Security intent:
- reduce prompt/tool injection blast radius;
- prevent external/tool content from directly causing writes;
- provide an enforcement seam for memory-poisoning protection;
- require trust re-establishment before cross-agent delegation;
- preserve least privilege and fail-closed behavior.

Adoption state: MEASURED_NOT_VERIFIED. Requires broader regression, security review and independent verification before canonical adoption.

## Immutable closure boundary
This roadmap is development work only. It does not alter Q10 frozen commit/tree, Q10 remains NOT_VERIFIED, Q11/Q12 remain BLOCKED, and Production remains NO-GO.
