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
- Evidence: recent threat-modeling work identifies tool poisoning in tool metadata as a high-impact MCP client-side risk and recommends static metadata analysis, decision-path tracking, behavioral anomaly detection, and user transparency.
- Deduplication: overlaps existing CK-NEXUS SkillLedger / connector-governance intent; new actionable detail is explicit metadata-integrity and upgrade-diff controls.
- Safe candidate: `MCP_METADATA_INTEGRITY_GATE`
- Required controls: signed or hash-pinned tool manifests where available; diff-on-upgrade; declared capabilities; write-action confirmation; fail closed on changed descriptors without re-review.
- Sources:
  - https://arxiv.org/abs/2603.22489
  - https://arxiv.org/abs/2601.07395

### Finding B — A2A is a communication standard, not an authority model
- Status: open protocol / ecosystem standard; not a CK-NEXUS-approved federation runtime.
- Evidence: official A2A materials distinguish agent-to-agent communication from MCP agent-to-tool/data integration; independent research reports specification-level risks including context injection, delegation identity loss, and rogue capability claims.
- Deduplication: A2A already exists in the CK-NEXUS protocol inventory; this is a security-maturity update.
- Safe candidate: `A2A_GATEWAY_EVALUATION`
- Required controls: authenticated agent identity, signed/attested capability claims, preserved delegation chain, context provenance, lease expiry, unknown-agent rejection, per-handoff evidence.
- Sources:
  - https://a2a-protocol.org/dev/
  - https://arxiv.org/abs/2609.10871

### Finding C — Local agent discovery must separate channel security from identity verification
- Status: draft protocol; not production-approved.
- Evidence: LAD-A2A v0.2.0-draft explicitly treats local networks as hostile by default and separates channel authentication from agent identity verification.
- Deduplication: new adjacent protocol candidate; no existing CK-NEXUS equivalent found.
- Safe candidate: `LOCAL_AGENT_DISCOVERY_THREAT_MODEL`
- Required controls: no trust from mDNS/TLS alone; authenticated discovery source; consent and resource limits; allowlist before federation.
- Source:
  - https://lad-a2a.org/spec/spec/

### Finding D — Thai ecosystem now provides a concrete red-team reference point
- Status: ecosystem/governance activity; not a certification or runtime dependency.
- Evidence: ETDA, NECTEC, TB-CERT, and NCSA held Thailand's first AI red-teaming event in July 2026, including banking-focused risk intelligence and CTF tracks spanning safety, security, privacy, fairness, and reliability.
- Deduplication: complements existing Thai governance tracking; new actionable reference is scenario-based red-team and sector-specific acceptance evidence.
- Safe candidate: `THAI_AI_REDTEAM_MAPPING`
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
