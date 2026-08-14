# Tenancy and Data Sovereignty

Status: architecture contract.

## Tenant boundary

Tenant/workspace identity is mandatory on tasks, sessions, memories, knowledge objects, capability decisions, credential leases, events, evidence, and execution journal entries. Absence of tenant context is fail-closed outside explicitly single-tenant development mode.

## Data classification

Minimum classes:

- `PUBLIC`
- `INTERNAL`
- `CONFIDENTIAL`
- `RESTRICTED`
- `SECRET_MATERIAL` (credentials/secret values; never model-visible unless a narrowly defined provider operation requires secret injection by broker)

Additional domain labels may include personal, financial, health, source-code, customer-support, and regulated data.

## Sovereignty policy

A policy may constrain processing/storage by region, provider, runtime type, retention, encryption posture, and cross-border transfer. Capability resolution hard-filters candidates that cannot satisfy these constraints.

## Credential isolation

Credentials are tenant-scoped and provider-scoped. A credential lease conveys permission to perform a bounded operation; it is not a transferable token. Connectors cannot export one provider's credential to another service.

## Memory/knowledge isolation

Retrieval always filters tenant before semantic ranking. Shared/public corpora are distinct namespaces with explicit provenance. Cross-tenant learning may only use approved aggregate/de-identified evaluation artifacts, never raw tenant memory by default.

## Evidence

Evidence records include tenant, data classification, redaction profile, region/runtime observation, policy hash, and retention class. Secret material is represented by fingerprints/references, not values.

## Deletion and retention

`never_forget` is not an authoritative retention policy. Supported retention intent includes ephemeral, session, operational, long-term, legal-hold, and user-pinned, subject to applicable deletion/legal policy. Deletion produces tombstone/audit evidence without retaining deleted sensitive content.
