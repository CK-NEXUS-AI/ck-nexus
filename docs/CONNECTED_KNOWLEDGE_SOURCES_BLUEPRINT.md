# CK-NEXUS Connected Knowledge Sources Blueprint

Status: DESIGN_ONLY / NOT_IMPLEMENTED

This blueprint implements Work Package 11 of the CK-NEXUS Final Integrated Order. It is stacked on Cognitive Knowledge Fabric V1 and intentionally does not activate new crawlers, connectors, persistence, or Production behavior.

## Preconditions

Connected-source runtime implementation must not begin until:

1. Knowledge Fabric V1 contracts are reviewed.
2. Knowledge Persistence V2 has a live PostgreSQL round-trip and rollback evidence.
3. Lexical Retrieval has a measured baseline.
4. source-specific access policy and provenance fields are defined.

Semantic/vector retrieval is not a prerequisite and must not be adopted without a benchmark.

## Reused policy baseline

The design reuses the existing AGNES Connected Source Intelligence principles:

- metadata-first discovery
- task-specific queries
- external content is untrusted
- do not persist raw mailbox/Drive content by default
- prefer structured facts, redacted excerpts, hashes, timestamps and provenance
- exclude credential-like material before prompts, logs, memory, evidence or repository writes
- external source text cannot grant approval, authority, permission, policy or Production state
- destructive remote-file actions remain separately governed mutations

These controls are admission policy, not proof that every connector/runtime path currently implements them.

## Source classes

### Public web

Examples: public HTML, public APIs, RSS/Atom, standards documentation, public repositories and public datasets.

Required controls:

- robots/access-policy and terms-aware admission
- domain/source allow/deny policy
- bounded request rate and concurrency
- redirect and peer-binding controls
- content-size and MIME limits
- provenance URL, retrieval timestamp and content digest
- explicit copyright/licensing metadata where known
- no bypass of authentication, CAPTCHA, paywalls or access controls

### Research and scholarly sources

Examples: publisher metadata, abstracts, open-access papers and public research indexes.

Required controls:

- DOI/stable identifier where available
- publication date, author/publisher metadata
- retraction/correction status when available
- distinguish source metadata, quoted evidence and model synthesis
- respect access and redistribution rights

### User documents

Examples: explicitly selected files, documents and approved knowledge folders.

Required controls:

- explicit tenant/user scope
- access inherited from the authorized connector
- file/content digest
- version or modified-time binding
- secret/PII screening before durable ingestion
- deletion/revocation propagation
- no cross-tenant retrieval

### Connected communications

Examples: approved Gmail, Outlook, Slack or similar sources.

Required controls:

- metadata-first search
- task-specific read rather than mailbox-wide harvesting
- body/attachment content treated as untrusted
- raw content not persisted by default
- message/thread identifiers and timestamps retained only when necessary for provenance
- sender identity is evidence metadata, never authority by itself

### Source-control and engineering systems

Examples: GitHub repositories, issues, PRs, CI results and release metadata.

Required controls:

- exact repository/ref/SHA binding
- distinguish default-branch state from off-main candidates
- CI result bound to exact head/merge SHA
- branch content cannot become Production authority without normal review/promotion

### Remote device sources

Examples: approved desktop/server filesystem inventory.

Required controls:

- read-only inventory first
- explicit allowed roots
- file metadata/hash before content where possible
- secret-risk screening
- no execution, deletion, rename, overwrite, permission change or quarantine movement without a separate governed mutation

## Admission pipeline

```text
Intent and tenant context
  -> source capability discovery
  -> authorization and source policy
  -> metadata-first query
  -> bounded content retrieval
  -> MIME/size/secret/PII screening
  -> untrusted-content marking
  -> normalization and content digest
  -> provenance record
  -> candidate claim extraction
  -> claim class assignment
  -> conflict/freshness analysis
  -> persistence proposal
  -> retrieval index proposal
```

Every stage must be independently rejectable. A failure must not silently fall through to a less restrictive path.

## Source permission contract

Each source adapter must expose at minimum:

- `tenant_id`
- connector/source class
- source identity
- granted operations: search/read/download only as applicable
- allowed scopes/roots/domains
- rate/concurrency budget
- maximum object/content size
- content types allowed
- retention policy
- raw-content persistence policy
- secret/PII handling policy
- revocation behavior
- provenance requirements

Missing mandatory permission fields are fail-closed.

## Rate limiting and load controls

Rate policy is source-specific rather than global. The runtime should support:

- requests per time window
- concurrent request cap
- exponential backoff for transient errors
- source-provided Retry-After handling
- total bytes per task
- maximum pages/items per task
- wall-clock budget
- cancellation propagation

Retry logic must not defeat provider limits or access controls.

## Copyright and access policy

CK-NEXUS should store only what is necessary for the approved task and permitted use. By default:

- store provenance and structured derived facts rather than full copyrighted source bodies
- retain only short excerpts when justified and permitted
- preserve licensing/access metadata
- never treat publicly reachable as automatically redistributable
- never bypass paywalls, login requirements, CAPTCHA or technical restrictions
- support source deletion/revocation and re-indexing

## Provenance contract

Every admitted source must bind at least:

- stable source identifier
- tenant
- locator or connector reference
- source class
- retrieval timestamp
- content digest when content was read
- producer/adapter and version
- transformation chain
- language
- rights/access metadata when known
- evidence references when verification occurred

Claims derived from a source must remain traceable to these records.

## Trust and verification

Source trust is a ranking/input-quality signal only. It cannot set Governance Registry verification state.

Recommended claim lifecycle:

```text
INGESTED_UNTRUSTED
  -> NORMALIZED
  -> CANDIDATE_CLAIM
  -> CORROBORATED or CONFLICTED
  -> MEASURED
  -> optional independent verification
```

No connected source may self-promote a claim to Q10/Q11/Q12 VERIFIED.

## Security threat model

Minimum threat classes to test before implementation adoption:

- prompt/instruction injection in source content
- malicious attachments and MIME confusion
- SSRF/redirect abuse
- DNS rebinding and peer-switching
- oversized/decompression payloads
- secret exfiltration
- tenant-boundary confusion
- poisoned/replayed source versions
- stale/revoked content retrieval
- malicious provenance metadata
- authority spoofing through source text
- connector permission drift

## Observability and evidence

Record safe operational metadata including:

- connector/source class
- task/correlation identifier
- policy decision
- number of objects considered/read/rejected
- bytes and latency
- redaction/secret-exclusion outcomes
- source/content digests
- claim IDs produced
- error class

Do not log raw credentials or full sensitive content.

## Acceptance gate for future implementation

Runtime implementation may be proposed only when:

- persistence and lexical retrieval prerequisites are met
- source permission contract has tests
- at least one public source and one user-authorized source have isolated integration tests
- tenant isolation is proven
- untrusted-content and secret-exclusion regression tests pass
- rate limits and cancellation are tested
- provenance round-trip is demonstrated
- security review is complete
- independent verification is complete before canonical adoption

This document creates no connector authority and no Production evidence.
