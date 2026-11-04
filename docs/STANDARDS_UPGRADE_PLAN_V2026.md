# CK-NEXUS Standards Upgrade Plan V2026

Status: Development plan only. This document does not change Q10/Q11/Q12 or Production authority.

## Operating rule
Every upgrade follows: Search-first -> Dedup -> Baseline measure -> Delta -> Benchmark -> Security review -> Independent verification -> Canonical adoption.

A candidate is rejected when it neither adds a new capability nor produces a measurable improvement. Passing CI is measurement evidence, not independent verification or Production authorization.

## Cross-cutting standards baseline
- OWASP GenAI LLM Top 10 2026
- OWASP Top 10 for Agentic Applications 2026
- OWASP Agent Control Standard 2026
- MCP 2026-07-28
- A2A 1.0
- OpenTelemetry GenAI Semantic Conventions
- NIST AI RMF 1.0 and NIST AI 600-1
- NIST SP 800-218A GenAI SSDF Community Profile
- ISO/IEC 42001:2023
- ISO/IEC 27001:2022
- ISO/IEC 23894:2023
- ISO/IEC 42005:2025

## 12-delta order and dedup decision
1. P0 Agent Security & Governance — EXTEND PR #201 with PR #149/#118/#192 controls. Add agentic threat coverage and runtime control-point mapping; do not create a second governance authority.
2. P0 MCP 2026-07-28 — EXTEND PR #155/#150. Replace transport-session assumptions with stateless protocol contracts and add current authorization/conformance tests.
3. P0 A2A — RECONCILE historical `post-p0/a2a-agent-admission-v1` before any new code; then add only missing A2A 1.0 contracts.
4. P1 GenAI Observability — EXTEND PR #155 and the canonical observability module; do not create a parallel telemetry authority.
5. P1 AI Risk/Evidence Mapping — EXTEND PR #201 + #189 + #153 so technical receipts trace into risk, governance, impact and auditor evidence.
6. P1 Tool/Connector Trust Fabric — EXTEND #155 + #149 + #113 + #118 + #192 into one admission/evidence lifecycle.
7. P1 Multi-model Routing V2 — EXTEND #106 + #154 + #143 + #112; route by measured capability and constraints rather than vendor identity.
8. P2 Memory V3 — RECONCILE #97 + #169 + #162 + #177; preserve exact lineage and proposal-only learning.
9. P2 Long-context / Document Intelligence — EXTEND #99 + #102 + #150 + #154 with retrieval, reranking, budgeting, provenance and conflict synthesis.
10. P2 Evaluation & Regression Fabric — EXTEND #103 + #111 + #153 + #189 into a mandatory before/after decision gate.
11. P2 Resilient Agent Execution — RECONCILE #183 + #179 + #104 on latest exact evidence before extending runtime execution.
12. P3 Multimodal Runtime — EXTEND #102 + #154 into modality-specific runtime permissions and evidence.

## Higher-than-original baseline additions
The plan adds three standards layers beyond the supplied 12-item list: NIST SP 800-218A for GenAI secure software development, ISO/IEC 23894 for AI risk management, and ISO/IEC 42005 for AI system impact assessment. They close the gap between runtime security controls and lifecycle/auditor/impact evidence.

## AI/vendor design inputs
External AI-vendor architecture guidance is informative only, never authority. Useful design principles are admitted only when they survive CK-NEXUS dedup, benchmarks and security review. Examples include layered guardrails, least-privilege tools, bounded retries, human intervention for high-risk actions, typed tool interfaces, tracing and eval-driven iteration.

## Hard boundaries
- Frozen Q10 commit/tree are immutable for this work.
- No release evidence is rewritten to make a development tree pass.
- No credential, paid action, legal acceptance or permission expansion is automated.
- No merge or deploy to Production.
- No builder/model/candidate may independently issue VERIFIED for itself.
- Independent verification and owner release authority remain separate gates.
