# CK-NEXUS Research Stack Integration V1

Status: Post-P0 development integration candidate.

Base lane: PR #244 SearXNG Development Runtime V1.

Integrated dependencies:
- PR #242 knowledge-driven research contracts and decision logic
- PR #243 PostgreSQL knowledge and research persistence
- PR #244 SearXNG development runtime

## Purpose

This integration tree proves that the research intelligence, persistence, and
self-hosted discovery runtime can coexist in one exact development tree.

It does not merge or close the source pull requests.

## Integration boundary

The tree adds the minimum persistence dependency closure required by the
research stack:

- idea_engine/knowledge_fabric.py
- idea_engine/knowledge_repository.py
- idea_engine/research_repository.py
- migrations/postgresql/004_knowledge_fabric_v2.sql
- migrations/postgresql/005_research_artifacts_v1.sql

It does not import branch-specific historical workflow files from PR #216 or
PR #243.

## Research persistence bridge

The canonical bridge is:

creator_app/global_knowledge/research_persistence_bridge.py

It translates:

- SourceRef into SourceRecord
- Claim into KnowledgeClaim
- ResearchCompilationArtifact into ResearchArtifactRecord

The bridge has no verification authority.

Rules:
- trust_score must be supplied explicitly
- claims remain OBSERVED when converted
- artifact claim IDs must exactly match supplied claims
- claim source IDs must belong to the research artifact
- worker artifacts marked VERIFIED are rejected
- persistence truth state is at most MEASURED_NOT_VERIFIED or REVIEW_REQUIRED

## Validation

Dedicated workflow:

.github/workflows/research-stack-integration-20260907.yml

The workflow validates one exact SHA by running:

1. research and discovery contract tests
2. knowledge persistence unit tests
3. research persistence unit tests
4. bridge invariant tests
5. PostgreSQL migration 004
6. PostgreSQL migration 005
7. live PostgreSQL round-trip tests
8. migration idempotency
9. SearXNG Compose validation
10. live SearXNG JSON readiness
11. runtime teardown

## Authority boundary

Successful development integration establishes measured compatibility only.

It does not establish:
- independent verification
- owner sign-off
- Q10/Q11/Q12 completion
- Production readiness
- certification
- permission for a worker to approve itself

The expected status after successful automated validation remains
MEASURED_NOT_VERIFIED.


## Continuous external research record — 2026-09-28

Run status: RESEARCH_UPDATED / NO_INSTALL / NO_PROMOTION / NO_PRODUCTION_CHANGE

### Finding A — MCP client-side tool poisoning remains a primary control gap
- Status: security research finding; not a protocol certification or vendor advisory.
- Deduplication: overlaps existing CK-NEXUS SkillLedger / connector-governance intent; new actionable detail is explicit metadata-integrity and upgrade-diff controls.
- Safe candidate: MCP_METADATA_INTEGRITY_GATE
- Required controls: signed or hash-pinned tool manifests where available; diff-on-upgrade; declared capabilities; write-action confirmation; fail closed on changed descriptors without re-review.
- Sources:
  - https://arxiv.org/abs/2603.22489
  - https://arxiv.org/abs/2601.07395

### Finding B — A2A is a communication standard, not an authority model
- Status: open protocol / ecosystem standard; not a CK-NEXUS-approved federation runtime.
- Deduplication: A2A already exists in the CK-NEXUS protocol inventory; this is a security-maturity update.
- Safe candidate: A2A_GATEWAY_EVALUATION
- Required controls: authenticated agent identity, signed/attested capability claims, preserved delegation chain, context provenance, lease expiry, unknown-agent rejection, per-handoff evidence.
- Sources:
  - https://a2a-protocol.org/dev/
  - https://arxiv.org/abs/2609.10871

### Finding C — Local agent discovery must separate channel security from identity verification
- Status: draft protocol; not production-approved.
- Deduplication: new adjacent protocol candidate; no existing CK-NEXUS equivalent found.
- Safe candidate: LOCAL_AGENT_DISCOVERY_THREAT_MODEL
- Required controls: no trust from mDNS/TLS alone; authenticated discovery source; consent and resource limits; allowlist before federation.
- Source:
  - https://lad-a2a.org/spec/spec/

### Finding D — Thai ecosystem now provides a concrete red-team reference point
- Status: ecosystem/governance activity; not a certification or runtime dependency.
- Deduplication: complements existing Thai governance tracking; new actionable reference is scenario-based red-team and sector-specific acceptance evidence.
- Safe candidate: THAI_AI_REDTEAM_MAPPING
- Required controls: scenario catalog, pre-production test evidence, data-disclosure checks, fairness/reliability cases, retest and closure records.
- Sources:
  - https://www.nstda.or.th/home/news_post/ai-red-teaming-20260706/
  - https://www.nstda.or.th/home/news_post/ai-governance-week-2026-20260629/

### Canonical disposition
- No external dependency installed.
- No dependency promoted to production.
- No Q10/Q11/Q12 gate closed.
- Findings are admissible as OBSERVED research inputs only until independently validated.
- Next safe work: implement schema-only controls and negative tests in a non-production branch; require evidence before any runtime integration.

## Continuous external research record — 2026-10-06

Run status: RESEARCH_UPDATED / NO_INSTALL / NO_PROMOTION / NO_PRODUCTION_CHANGE

### Finding E — Workload identity is a concrete control candidate
- Status: stable identity standard; SPIRE is a production-ready implementation of SPIFFE APIs.
- Evidence: SPIFFE defines stable workload identity and a Workload API; SPIRE performs node/workload attestation and issues SVIDs only after configured conditions are satisfied.
- Deduplication: complements CK-NEXUS Agent Identity and Credential Reference; it does not replace CK-NEXUS authorization, lease, policy, or evidence authority.
- Safe candidate: SPIFFE_AGENT_IDENTITY_PROFILE
- Required controls: map SPIFFE identity to CK-NEXUS agent identity; short-lived SVID handling; trust-domain configuration; expiry/rejection handling; fail closed on attestation or identity validation failure.
- Sources:
  - https://spiffe.io/docs/latest/spiffe-specs/spiffe/
  - https://spiffe.io/docs/latest/spiffe-specs/spiffe_workload_api/
  - https://spiffe.io/docs/latest/spire-about/spire-concepts/

### Finding F — OpenTelemetry GenAI observability is useful, but conventions remain a moving boundary
- Status: observability standard family; GenAI agent conventions remain development/moving and have moved into a dedicated repository.
- Evidence: OpenTelemetry documents GenAI telemetry and agent observability while explicitly marking semantic conventions as Development and noting the GenAI conventions move.
- Deduplication: complements CK-NEXUS Evidence Engine and runtime observability; telemetry is never verification authority.
- Safe candidate: CKNEXUS_OTEL_AGENT_EVIDENCE_PROFILE
- Required controls: correlation IDs for agent/run/lease/policy/tool/verifier/evidence; sensitive-data redaction; convention version pinning; telemetry integrity checks; no promotion of telemetry alone to VERIFIED.
- Sources:
  - https://opentelemetry.io/docs/specs/semconv/
  - https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
  - https://opentelemetry.io/blog/2026/genai-observability/

### Finding G — NIST has formalized an AI Agent Standards Initiative
- Status: standards/governance initiative; not a runtime dependency or certification.
- Evidence: NIST's initiative explicitly targets interoperable and secure agents and names standards, open protocols, security, and identity as strategic pillars.
- Deduplication: upgrades the existing NIST tracking lane from general standards watch to a named initiative tracker.
- Safe candidate: NIST_AGENT_STANDARDS_TRACKER
- Required controls: track official releases/RFIs/concept papers; map normative requirements to CK-NEXUS controls; never infer compliance from participation or alignment alone.
- Source:
  - https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure

### Finding H — Enterprise agent security is converging on centralized authority layers
- Status: ecosystem trend; not evidence of a single standard.
- Evidence: current research signals emphasize cryptographic identity, short-lived access, per-tool authorization, human approval, runtime guardrails, and decision-chain auditing; enterprise adoption remains constrained by integration and security readiness.
- Deduplication: these controls are already architectural goals in CK-NEXUS Enforcement Stack vNext, so no second orchestration authority should be introduced merely to duplicate them.
- Safe candidate: ENFORCEMENT_STACK_CONTROL_CROSSWALK_20261006
- Required controls: compare existing CK-NEXUS controls against current ecosystem patterns; implement only uncovered controls; preserve one governance authority.
- Sources:
  - https://www.okta.com/company/careers/opportunity/8241309
  - https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative

### Immediate disposition
- SPIFFE/SPIRE: OBSERVED / schema-only identity mapping candidate.
- OpenTelemetry GenAI: OBSERVED / version-pinned telemetry schema candidate.
- NIST Agent Standards Initiative: OBSERVED / standards tracker candidate.
- Enterprise authority-layer trend: OBSERVED / architecture crosswalk only.
- No dependency installation.
- No runtime authority change.
- No Q10/Q11/Q12 promotion.
- No Production status change.
- Next safe implementation lane: schema-only profiles + negative tests, then independent verification.

## Continuous external research record — 2026-10-06 / security delta

Run status: RESEARCH_UPDATED / NO_INSTALL / NO_PROMOTION / NO_PRODUCTION_CHANGE

### Finding I — Agent skill/tool supply chain needs provenance admission, not just dependency scanning
- Status: active security trend; incident evidence, not a certification.
- Evidence: current supply-chain activity affecting packages and CI actions reinforces that agent ecosystems inherit ordinary software supply-chain compromise while adding tool/skill metadata and runtime capability surfaces.
- Deduplication: extends existing agent/MCP/skill admission architecture; does not create a second package manager or runtime.
- Safe candidate: AGENT_SKILL_PROVENANCE_GATE
- Required controls: immutable source reference, commit/tree/file hashes, dependency manifest, signer/provenance where available, capability declaration, security review, admission certificate, upgrade diff, automatic quarantine on provenance drift.
- Sources:
  - https://www.bleepingcomputer.com/news/security/github-actions-re-enabled-with-mini-shai-hulud-payload-still-active/
  - https://www.nvd.nist.gov/

### Finding J — Dynamic malicious skill injection deserves a first-class negative test
- Status: research finding; not a production threat-rate claim.
- Evidence: recent research demonstrates runtime injection of malicious logic through natural-language documentation/skill surfaces in agentic coding environments.
- Deduplication: complements MCP metadata-integrity controls and agent admission; the new actionable layer is testing behavior after admission rather than trusting static review alone.
- Safe candidate: AGENT_DYNAMIC_SKILL_INJECTION_TEST
- Required controls: clean baseline, admitted skill hash, controlled mutation, behavioral diff, privilege/tool-call diff, evidence capture, automatic rejection on unauthorized capability change.
- Source:
  - https://arxiv.org/abs/2606.16287

### Finding K — Long-horizon and adversarial evaluation should be part of deployment readiness
- Status: evaluation research; not a production certification.
- Evidence: current agent evaluations increasingly test long-horizon behavior, exploitability, coordination, monitoring, and runtime defenses rather than only task success.
- Deduplication: extends CK-NEXUS deployment readiness and behavioral-control candidates; benchmark scores remain external evidence, not CK-NEXUS VERIFIED state.
- Safe candidate: AGENT_LONG_HORIZON_CONTROL_EVAL
- Required controls: bounded scenarios, explicit success/failure criteria, adversarial cases, tool/privilege telemetry, timeout and budget controls, reproducible corpus/version, raw results, independent evaluator, evidence hash.
- Sources:
  - https://arxiv.org/pdf/2605.11086
  - https://arxiv.org/abs/2606.05342

### Immediate disposition — security delta
- AGENT_SKILL_PROVENANCE_GATE: OBSERVED / P1 candidate.
- AGENT_DYNAMIC_SKILL_INJECTION_TEST: OBSERVED / P1 negative-test candidate.
- AGENT_LONG_HORIZON_CONTROL_EVAL: OBSERVED / P2 evaluation candidate.
- No dependency installation.
- No external runtime authority.
- No automatic trust promotion from benchmark or incident data.
- Next safe lane: add schema/test contracts only; require CI and independent reproduction before merge.
