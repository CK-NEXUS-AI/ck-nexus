# CK-NEXUS — 18 Core Capabilities Execution Plan

Status: DEVELOPMENT / GOVERNANCE CONTROLLED
Date: 2026-09-05
Base philosophy: reuse existing capability first; do not create duplicates.
Authority effect: NONE

## Operating rules

- Latest exact evidence wins.
- Search first, then delta-only implementation.
- Reuse existing CK-NEXUS components before adding new ones.
- Every capability must have a measurable acceptance criterion.
- Development evidence does not promote Q10 or Production state.
- No AI self-approval.
- No external publish, paid action, credential disclosure, or authority change without the required human permission.

## Priority P0

### 1. Prompt Mode Registry

Current base:
- Creator Intelligence mode registry candidate exists on this development branch.
- Existing canonical prompt policy and specialist agents can be reused.

Target:
- Standard transparent modes such as research, expert, compare, seo, creator.
- Output contract per mode.
- Explicit prohibited behavior per mode.
- Unknown mode fails closed.
- Modes are CK-NEXUS modes, not "secret ChatGPT commands".

Acceptance:
- Registry is machine-readable.
- Unit tests cover aliases, unknown modes, source-required modes, and no implicit publishing.
- Prompt mode cannot override runtime/system policy.
- Documentation and examples match executable behavior.

Status: IMPLEMENTED_CANDIDATE / MEASURED_NOT_VERIFIED

### 2. Provider Capability & Pricing Registry

Current base:
- Provider Registry, Provider Router, Credential Broker, provider capability objects exist.
- Some provider metadata contains hard-coded free/freemium claims that can become stale.

Target:
- Separate consumer free plan from API free tier.
- Record capability, pricing state, quota model, checked_at, source, scope, uncertainty.
- Router consumes verified capability/pricing metadata but never treats stale marketing text as truth.

Acceptance:
- No provider is classified "free" without source + checked_at + scope.
- Pricing state supports UNKNOWN, VERIFIED_FREE, FREEMIUM, TRIAL, PAID.
- Stale entries are detectable.
- Router behavior is tested when pricing is missing/stale.
- Credentials remain handled only through approved broker paths.

Status: PARTIAL_BASE / P0_REFACTOR_REQUIRED

### 3. Research + Source Verification Engine

Current base:
- Researcher agent, provider web-search capability, Idea Engine source_refs, evidence/governance components exist.

Target:
- Search + collect + classify source quality + freshness + claim support.
- Separate fact, analysis, inference, prediction, opinion.
- Preserve URL/source identity and access time.

Acceptance:
- Every factual research claim can point to at least one source object.
- Source object records source URL/ID, observed_at, publisher/type, freshness.
- Unsupported claims are labeled, not silently promoted.
- Conflicting sources remain visible.
- Tests cover stale, conflicting, missing, and low-trust sources.

Status: PARTIAL_BASE / DESIGN_AND_IMPLEMENT

### 4. Originality + Provenance Gate

Current base:
- Evidence, provenance-oriented IdeaGraph relations, source refs, content repurpose policy exist.

Target:
- Track source lineage for content and ideas.
- Detect trivial duplication/rewrite.
- Record added value and transformation notes.
- Preserve provenance through repurpose and workflow steps.

Acceptance:
- Each publishable draft has source lineage or explicit "original input" origin.
- Reused material records transformation.
- Gate blocks content with missing provenance where required.
- Gate never invents ownership/originality certainty.
- Tests cover source reuse, partial transformation, and unknown provenance.

Status: PARTIAL_BASE / GATE_MISSING

### 5. Fact / Claim Verification Gate

Current base:
- Editorial Reviewer can flag unsupported claims.
- Evidence/security governance patterns already fail closed.

Target:
- Extract factual claims.
- Bind claims to supporting evidence.
- Assign VERIFIED, PARTIAL, UNSUPPORTED, CONFLICTED.
- Prevent unsupported factual claims from passing a publish-ready gate.

Acceptance:
- Claim object has text, source refs, status, confidence, checked_at.
- Unsupported and conflicted claims cannot become publish-ready automatically.
- Human override, if permitted, is explicit and audited.
- Tests cover statistics, dates, quotations, product/pricing claims and conflicting evidence.

Status: PARTIAL_BASE / GATE_MISSING

## Priority P1

### 6. Multi-Provider AI Router

Current base:
- Provider Router, Credential Broker, provider capability model, local/cloud routing exist.

Target:
- Route by capability, cost, latency, privacy, availability and policy.
- Fail over safely.
- Record routing decision and result.

Acceptance:
- Deterministic routing policy for identical inputs/state.
- No credential leakage in logs.
- Failover is bounded and circuit-breaker aware.
- Routing decision evidence includes provider, capability reason, policy and timestamp.
- Tests cover unavailable, slow, forbidden and local-preferred providers.

Status: PROVEN_BASELINE / EXTEND_ONLY

### 7. Multimodal Capability Layer

Current base:
- Text provider routing exists.
- No complete canonical multimodal abstraction across image/video/audio/presentation.

Target:
- Capability taxonomy independent of vendor:
  text, image generation/editing, video, STT, TTS, music, presentation, design.

Acceptance:
- Capability registry is vendor-neutral.
- Provider adapter declares exact supported capabilities.
- Router refuses unsupported modality.
- Binary/media data has provenance, size/type limits and privacy classification.
- At least one tested adapter per adopted modality before claiming support.

Status: GAP / DESIGN_FIRST

### 8. SEO / AEO / GEO Discovery Layer

Current base:
- Research and creator components can be reused.
- No canonical dedicated discovery layer.

Target:
- Search intent, content gaps, structure, people-first quality, evidence/citation readiness.
- Treat AEO/GEO as discovery/measurement concepts, not ranking guarantees.
- Support local/language targeting where evidence is available.

Acceptance:
- Output separates observed search data from strategy inference.
- No guaranteed ranking claims.
- Source-backed keyword/topic evidence.
- Quality checks for originality, usefulness and unsupported claims.
- Measurement connector is optional and permissioned.

Status: DESIGN_CANDIDATE

### 9. Creator Workflow Orchestrator

Current base:
- Content Strategist, Script Writer, Repurpose Studio, Editorial Reviewer, Idea Engine, workflow/orchestration components.

Target:
Research -> Plan -> Create -> Verify -> Review -> Repurpose -> Optimize -> Publish Draft -> Measure -> Learn.

Acceptance:
- Every stage has explicit input/output contract.
- Required gates cannot be skipped silently.
- Publish Draft is not equivalent to external publish.
- Workflow is resumable and idempotent where practical.
- Failure state records reason and evidence.

Status: PARTIAL_BASE / ORCHESTRATION_DELTA

### 10. Analytics Feedback Loop

Current base:
- Observability/metrics exist for system runtime.
- Creator performance analytics is not complete.

Target:
- Ingest reach, engagement, saves, clicks, conversions, watch-time when authorized.
- Normalize platform metrics.
- Feed evidence into strategy proposals.

Acceptance:
- Metric source, time window and platform are preserved.
- Missing metrics remain unknown, never zero-filled silently.
- Recommendations distinguish correlation from causation.
- Learning output is proposal-only until approved.
- Connector permissions and consent are enforced.

Status: PARTIAL_OBSERVABILITY / CREATOR_ANALYTICS_GAP

## Priority P2

### 11. Content Strategy Engine

Current base:
- Content Strategist agent.

Acceptance:
- Audience, content pillars, objectives and measurable metrics are explicit.
- Strategy cites evidence when based on external facts.
- Strategy revisions preserve history.
- No invented audience research.

Status: EXISTING_BASE / EXTEND

### 12. Script & Copy Generation

Current base:
- Script Writer.

Acceptance:
- Platform-specific output contract.
- Hook/body/CTA structure where appropriate.
- Factual claims sent to Claim Verification Gate.
- No unsupported testimonial/statistic generation.
- Tests for timing/length and required fields.

Status: EXISTING_BASE / EXTEND

### 13. Repurpose Engine

Current base:
- Repurpose Studio.

Acceptance:
- Preserves core message.
- Records source content/provenance.
- Platform variants are structurally distinct, not simple truncation.
- Unsupported new claims are blocked.
- Tests cover multiple target formats.

Status: EXISTING_BASE / EXTEND

### 14. Content Calendar / Scheduler

Current base:
- Generic scheduler/automation concepts exist; creator calendar is not canonical.

Acceptance:
- Draft schedule can be created without publishing authority.
- Timezone is explicit.
- Duplicate jobs are idempotent.
- Reminder and publish actions are separated.
- External publish still requires connector policy/authority.

Status: GAP / BUILD_ON_SCHEDULER

### 15. Hook & Creative Pattern Library

Current base:
- Hooks are already part of strategist/script behavior but no governed pattern library.

Acceptance:
- Pattern is stored as a reusable template, not a performance guarantee.
- Pattern has category, context, example and provenance.
- No fabricated percentage performance.
- Analytics can rank patterns only from measured data.
- User can inspect why a pattern was selected.

Status: PARTIAL_CONCEPT / LIBRARY_GAP

### 16. Publishing Connector Fabric

Current base:
- Connector Fabric, Credential Broker, API/MCP/integration security.

Acceptance:
- Each connector declares scopes/capabilities.
- Dry-run supported where platform allows.
- External publish requires explicit authority.
- Idempotency key prevents duplicate publishing.
- Audit includes who/what/when/where/result.
- Secrets never appear in evidence.

Status: PARTIAL_BASE / PLATFORM_ADAPTERS_REQUIRED

### 17. Privacy & Consent Engine

Current base:
- Privacy Firewall.
- Personal Intelligence Consent Ledger.
- Data classification and redaction.

Acceptance:
- Data item records source, purpose and classification.
- Consent is explicit, scoped, revocable and time-aware.
- Retention/deletion policy is represented.
- External disclosure is fail-closed.
- Secret material is never externally disclosed through normal policy.
- Tests cover revoke/expiry/redaction/disclosure denial.

Status: STRONG_PARTIAL_BASE / PERSISTENCE_AND_RETENTION_DELTA

### 18. Learning & Optimization Layer

Current base:
- Idea Engine proposal model.
- Learning/knowledge candidates and evidence-governance patterns exist.

Target:
- Use measured outcomes to propose improvements in strategy, provider selection and workflow configuration.
- Never mutate authority rules or verification state autonomously.

Acceptance:
- Learning output is proposal-only by default.
- Every proposal links evidence.
- No self-approval.
- No automatic Q10/Production status mutation.
- Rejected proposals remain traceable.
- Benchmark before canonical adoption.

Status: PARTIAL_BASE / GOVERNED_LEARNING_DELTA

## Execution order

Wave A — P0 foundation:
1 -> 2 -> 3 -> 4 -> 5

Wave B — orchestration:
6 -> 7 -> 8 -> 9 -> 10

Wave C — creator expansion:
11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17 -> 18

## Definition of Done for any capability

A capability is not "done" merely because code exists. Minimum DoD:

1. Scope and authority boundary documented.
2. Search-first comparison proves it is not a duplicate.
3. Interface/contract defined.
4. Implementation exists on Development branch.
5. Unit tests pass.
6. Integration tests pass where applicable.
7. Security/privacy review completed.
8. Evidence produced with exact subject/version/time.
9. Documentation matches executable behavior.
10. Independent verification is performed where required.
11. Canonical adoption happens only after review.
12. No Q10/Production status is changed by Development evidence.

## Project state boundary

This plan does not alter:
- Q10 = NOT_VERIFIED
- Q11 = BLOCKED
- Q12 = BLOCKED
- Production = NO-GO / NOT CERTIFIED
