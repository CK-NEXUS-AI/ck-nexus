# Base44 / Solas Runtime Integrity Findings

Status: OBSERVATION_ONLY / 2026-08-15 snapshot

## Verified runtime observations

Base44 app: `Solas`
App ID: `6a7f2975e682d5f59c2a182e`

Live Base44 connector catalog reported:

- 78 connector types available
- 17 connectors currently connected/active
- Gorgias is active with read scopes
- Intercom is active
- Gmail, Google Calendar, Google Drive, Google Sheets, Google Analytics, Slack, GitHub, Notion, LinkedIn, TikTok, Instagram, Wix, Outlook, Linear and Square are among the active connectors

The `CkNexusConnector` entity contains 18 records: 17 marked ACTIVE and Facebook Pages marked PENDING_AUTH. This is consistent with the live connector count only when the pending record is excluded.

## Integrity mismatches

### Brain summary vs. skill records

`CkNexusBrain` currently reports:

- `total_skills = 63`
- `total_capabilities = 240`
- `model_state = CONTINUOUS_LEARNING`
- `overall_status = OPERATIONAL`

However, direct entity reads found 189 `CkNexusSkill` records and every returned `skill_id` is null. Sampled records also have null names, descriptions, source fields, activity flags and performance scores.

Conclusion: `total_skills=63` is not currently supported by normalized skill records and must not be imported as verified capability evidence.

### Memory records

Direct entity reads found 192 `CkNexusMemory` records and every returned `memory_id` is null. Sampled records also have null content, source, category, persistence and retention fields.

Conclusion: existing memory rows must be treated as malformed/unverified external records until reconstructed from a trustworthy source or discarded under an approved migration plan.

### Connector cache vs. live connector API

`CkNexusConnector` is useful as a cache but is not authoritative. Examples of possible drift include abbreviated or empty scopes in entity records while the live connector API reports provider-native granted scopes.

Authority rule: live connector API > verified CK observation > Base44 entity cache > generated summary.

## Required normalization before federation

Each external skill must have at minimum:

- stable capability/skill ID
- name and description
- source/provider
- source version or capture timestamp
- input/output contract
- risk class
- side-effect class
- evidence/provenance reference
- validation status
- duplicate/semantic hash

Each external memory item must have at minimum:

- stable memory ID
- content hash
- source and source type
- capture timestamp
- data classification
- retention policy
- provenance
- confidence/verification state
- tenant/workspace ownership

Each connector observation must have:

- integration type
- runtime source
- observed status
- provider-native scopes
- observation timestamp
- health freshness
- capability mapping version
- authorization boundary

## Migration policy

Do not delete or rewrite Base44 records automatically. Migration should be append-only and reversible:

1. snapshot current entity counts and IDs
2. read live connector state
3. generate normalized candidates
4. validate candidates against CK schemas
5. quarantine malformed records
6. register only validated capability records
7. write provenance/evidence
8. compare counts and hashes
9. require owner approval before destructive cleanup

## Security consequence

The existing `auto_connect_enabled`, `auto_repair_enabled`, `continuous_mode`, `never_forget`, or credit-related flags are advisory metadata only. They do not authorize automatic OAuth consent, account creation, token distribution, quota evasion, production mutation, or unbounded self-modification.
