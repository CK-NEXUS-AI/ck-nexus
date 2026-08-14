# CK-NEXUS × Base44 Federation Architecture

Status: SPEC_ONLY / NOT_PRODUCTION_BINDING

## Purpose

Integrate the existing Base44/Solas runtime with CK-NEXUS without making Base44 metadata, generated skills, or token automation authoritative by itself.

## Authority split

- Base44/Solas is an External Execution & Connector Plane.
- CK-NEXUS is the policy, capability-validity, provenance, evidence, and release-governance source of truth.
- Provider or connector state reported by Base44 is an observation, not an authorization decision.
- No external runtime may bypass CK-NEXUS Trust Fabric, Capability Authority, AGNES execution controls, or Evidence Fabric for impactful actions.

## Target flow

User / Event
  -> CK-NEXUS Access Gateway
  -> Cognitive Governor / Intent Compiler
  -> Task DAG
  -> Capability Registry
  -> Policy + Risk + Cost + Data Classification
  -> Capability Grant
  -> Credential Lease
  -> AGNES
  -> Base44 Federation Adapter
  -> Base44 connector/runtime
  -> Verification
  -> Evidence + Durable Action Journal
  -> Event Fabric
  -> State Commit

## Federation Adapter responsibilities

1. Runtime discovery
   - list available Base44 connectors
   - read current authorization/health/scopes
   - expose normalized capability observations

2. Connector normalization
   - convert Base44 integration types into CK-NEXUS connector manifests
   - normalize scopes and capability names
   - retain provider-native scopes as evidence metadata

3. Capability normalization
   - never trust `total_capabilities`, `total_skills`, or generated skill records without validation
   - deduplicate by semantic capability ID plus contract hash
   - require provenance and verification state

4. Memory/knowledge ingestion
   - Base44 memory is an external source, not canonical CK-NEXUS memory
   - each imported item requires source, capture time, integrity status, classification, retention policy, and provenance
   - `never_forget` is not accepted as a CK-NEXUS retention policy

5. Credential boundary
   - Base44 OAuth/token material remains inside the provider/runtime boundary
   - CK-NEXUS receives capability/health observations and opaque credential lease references only
   - no API key copying, token distribution, cross-provider token reuse, or quota-evasion rotation

6. Side effects
   - Base44 may execute an impactful action only when AGNES presents a valid CK-NEXUS capability grant and policy decision
   - high-impact actions remain approval-aware
   - frontend enable/disable state is never treated as authorization

7. Evidence
   Every external action should produce:
   - request/task ID
   - adapter ID/version
   - provider/integration type
   - normalized capability ID
   - policy decision ID
   - capability grant ID
   - credential lease reference (opaque)
   - start/end timestamps
   - normalized result class
   - provider receipt/reference when available
   - verifier result
   - evidence hash/provenance

## Source precedence

When sources disagree, use this precedence for runtime truth:

1. direct provider/connector API observation
2. Base44 connector catalog live status
3. CK-NEXUS verified external-runtime observation
4. Base44 entity cache
5. generated summaries/brain counters

No lower-precedence source may overwrite higher-precedence verified evidence.

## Normalized lifecycle

DISCOVERED -> OBSERVED -> VALIDATED -> REGISTERED -> HEALTHY
                                   \-> DEGRADED
                                   \-> REAUTH_REQUIRED
                                   \-> QUARANTINED
                                   \-> REVOKED

Generated skill/memory records begin as `UNVERIFIED_EXTERNAL_CANDIDATE` and never enter the active Capability Registry automatically.

## Failure model

- malformed entity record: quarantine record, do not infer missing values
- stale scope cache: prefer live connector status
- OAuth expired: `REAUTH_REQUIRED`, no automatic bypass
- provider rate limit: retry within provider policy, then fallback to another already-authorized compatible provider or local runtime
- missing evidence: fail closed for impactful action
- capability mismatch: no execution
- unknown side effect: require approval or deny

## Runtime implementation boundary

This document does not authorize runtime restructuring, production deployment, credential migration, token mutation, repository security changes, or Q10-Q16 promotion.

Runtime Phase 1 after Q10 should implement:

- Base44 read-only discovery adapter
- normalized external-runtime observation type
- connector/capability mapper
- stale-cache conflict detector
- provenance/evidence writer
- contract tests using recorded fixtures

Only after those pass should write-capable Base44 actions be bound through AGNES and Trust Fabric.
