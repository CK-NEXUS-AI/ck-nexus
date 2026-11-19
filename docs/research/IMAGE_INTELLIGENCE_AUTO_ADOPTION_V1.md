# CK-NEXUS Image Intelligence Auto-Adoption V1

Status: DEVELOPMENT CANDIDATE
Authority effect: NONE
Production: NO-GO

## Objective

Turn large image collections into reusable CK-NEXUS development intelligence without
treating social-media graphics, screenshots, infographics, or extracted text as
canonical truth.

## Pipeline

1. Ingest
   - preserve source reference
   - SHA-256 every image
   - assign collection and sequence
   - never overwrite originals

2. Vision extraction
   - scene/category summary
   - text and labels
   - tool/vendor/entity names
   - workflows
   - capabilities
   - numeric/marketing claims
   - privacy/security claims
   - UI/UX patterns

3. Claim typing
   - fact
   - tool
   - workflow
   - metric
   - prompt pattern
   - privacy
   - product
   - pricing
   - capability

4. Trust and verification
   - image is discovery evidence only
   - vendor, pricing, numeric, privacy, and current claims require fresh verification
   - record source, checked_at, and evidence digest
   - contradictory claims remain unresolved until evidence wins

5. Canonical dedup
   - search CK-NEXUS main and active development work
   - classify REUSE, DUPLICATE, VERIFY, BENCHMARK, DEV_CANDIDATE, QUARANTINE, or REJECT
   - reuse existing capability before building a parallel system

6. Proposal generation
   - convert useful deltas into Idea Engine proposals
   - preserve image source refs
   - state assumptions, risks, evidence needed, and next experiments

7. Benchmark
   - compare against current baseline
   - prove measurable benefit before adoption

8. Security and privacy review
   - classify personal, sensitive, and secret material before external processing
   - redact secrets from extracted text and evidence
   - preserve provenance

9. Automatic development staging
   - validated low-risk deltas may create tests and Draft PR candidates
   - never auto-merge
   - never auto-publish
   - never change Q10, Q11, Q12, or Production authority

10. Independent verification and canonical adoption
   - independent verification remains required
   - human authority remains required where governance specifies it
   - canonical adoption only after gates pass

## Canonical reuse

Reuse existing:
- AI Gateway capability taxonomy
- Privacy Firewall
- Idea Engine
- SelfCapabilityManager
- Capability Registry
- Connector Evidence Ledger
- Development execution evidence
- Provider routing

## Current canonical gap

ModelCapability.VISION exists, but the current GatewayRequest and provider adapter
invocation are still text-only. A follow-up delta should introduce a provider-agnostic
image input contract with digests, source refs, data classification, and explicit
external-processing permission.

## Album workflow

For a collection such as Pins 470:

album -> manifest -> image batches -> normalized insights -> claim ledger ->
verification queue -> canonical dedup -> capability genealogy -> benchmark queue ->
development candidates

Recommended outputs:
- image-manifest.jsonl
- insights.jsonl
- claims.jsonl
- verification-queue.jsonl
- capability-candidates.jsonl
- duplicate-map.json
- rejected-or-quarantined.jsonl
- batch-summary.md

## Automation boundary

Safe to automate:
- hashing
- metadata extraction
- classification
- dedup search
- verification queue creation
- benchmark preparation
- test generation
- development branch and Draft PR creation when evidence is sufficient

Never automatic:
- production merge or deploy
- paid service activation
- credential disclosure
- legal acceptance
- Q10 authority transition
- independent reviewer attestation
- owner sign-off

Latest exact evidence wins.
