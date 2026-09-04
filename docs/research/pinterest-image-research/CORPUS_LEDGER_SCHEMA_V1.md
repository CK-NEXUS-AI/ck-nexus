# Pinterest Image Research Corpus Ledger V1

Status: DEVELOPMENT RESEARCH LEDGER
Authority effect: NONE
Production effect: NONE
Owner directive: ../PINTEREST_IMAGE_RESEARCH_OWNER_DIRECTIVE_VERBATIM.md

## Corpus target

- Minimum target: 1000 distinct research images when publicly accessible.
- Seed-derived expansion plus related-topic discovery.
- Exact duplicates are counted once by SHA-256.
- Image-size/CDN variants of the same underlying asset must not inflate the count.
- No login, CAPTCHA, anti-bot, paywall, or access-control bypass.

## Per-image record

Each image record should preserve:

- record_id
- image_sha256
- perceptual_duplicate_group when available
- original_source_url
- pinterest_pin_url
- pinterest_pin_id
- image_url
- width / height / media_type
- title
- description
- publisher / author
- published_at / checked_at
- source_platform
- source_language
- collection_query
- discovery_parent_id
- visible_text_verbatim
- headings
- body_text
- keywords
- entities / vendors / tools / frameworks / APIs / websites
- architecture_or_workflow
- prompt / content / SEO / AEO / GEO / automation ideas
- numeric_or_marketing_claims
- privacy_or_security_claims
- extracted_claims
- claim_verification_state
- verification_sources
- matched_pinterest_results
- matched_external_results
- image_vs_web_comparison
- duplicate_of
- ck_nexus_existing_capability_refs
- ck_nexus_reuse_decision
- ck_nexus_delta
- priority_p0_p3
- benchmark_needed
- security_privacy_implications
- free_freemium_paid_ui_api
- usefulness_score
- evidence_state
- notes

## Evidence states

DISCOVERED -> METADATA_CAPTURED -> PIXEL_SCANNED -> CLAIMS_EXTRACTED ->
WEB_COMPARED -> VERIFIED_OR_REVIEWED -> DEDUPED -> CK_NEXUS_MAPPED

A missing stage must remain explicitly pending. Social-media imagery is discovery
evidence, not canonical authority.

## CK-NEXUS decision states

REUSE / DUPLICATE / VERIFY / BENCHMARK / DEV_CANDIDATE / QUARANTINE / REJECT

No image-derived record may change Q10/Q11/Q12 or Production authority.
