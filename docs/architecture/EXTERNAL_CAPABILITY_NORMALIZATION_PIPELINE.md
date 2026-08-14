# External Capability Normalization Pipeline

Status: SPEC_ONLY

## Goal

Convert capabilities, skills, memories, connector state and provider metadata from external runtimes into CK-NEXUS records that are comparable, deduplicated, policy-aware and evidence-backed.

## Pipeline

External Runtime Observation
  -> Schema Validation
  -> Source Freshness Check
  -> Provenance Capture
  -> Semantic Normalization
  -> Duplicate Detection
  -> Risk / Side-Effect Classification
  -> Contract Validation
  -> Capability Test
  -> Evidence Record
  -> Registry Candidate
  -> Approval if required
  -> Registered Capability

## Candidate states

- RAW_EXTERNAL
- MALFORMED
- STALE
- DUPLICATE
- CONFLICT
- VALIDATED_CANDIDATE
- QUARANTINED
- REGISTERED
- REVOKED

Only `VALIDATED_CANDIDATE` may proceed to registration.

## Deduplication identity

A candidate should not be considered unique just because it came from a different AI model or website.

Proposed identity tuple:

`semantic_capability_id + input_contract_hash + output_contract_hash + side_effect_class`

Provider-specific implementation details remain variants beneath the same semantic capability.

Example:

- OpenAI web search
- Perplexity search
- Gemini grounding/search

may all map to `research.web.search_grounded`, while preserving provider-specific limits, citations, latency, cost and trust scores as implementation metadata.

## Capability validity

A capability is valid only when CK-NEXUS has evidence for:

1. a concrete callable interface or executable workflow
2. an input/output contract
3. permission/auth requirements
4. risk/side-effect classification
5. a successful contract or fixture test
6. provenance
7. freshness metadata

A textual model description is knowledge, not an executable capability.

## Knowledge ingestion

Public documentation, owner-provided files, provider metadata and observed outputs may be ingested as knowledge with provenance. Proprietary hidden prompts, model weights, private training data or unlicensed content are not treated as extractable skills.

Knowledge candidates are deduplicated separately from executable capabilities.

## Memory normalization

Replace `never_forget` with explicit retention policy:

- ephemeral
- session
- operational
- long_term
- legal_hold
- user_pinned

Every memory record requires tenant ownership, classification, source, content hash, timestamps and deletion/retention policy.

## Connector normalization

Connector availability is distinct from capability authorization.

For each connector maintain:

- catalog availability
- connection state
- provider-native scopes
- normalized capabilities
- health freshness
- tenant/account binding
- last successful verification
- risk classes
- approval requirements

A connected connector with insufficient scope is not capability-ready.

## Provider selection

The router selects among already-authorized provider implementations using task fit, verification history, policy, data classification, cost, quota, latency and health.

It must not create accounts or keys, distribute credentials across unrelated services, or rotate accounts/keys to evade provider limits.

## Learning loop

Execution Evidence
  -> Evaluator
  -> Historical Accuracy / Reliability Metrics
  -> Capability Score Update
  -> Router Preference Update

Learning updates routing metadata and knowledge; it does not silently modify security policy, authority boundaries or production code.
