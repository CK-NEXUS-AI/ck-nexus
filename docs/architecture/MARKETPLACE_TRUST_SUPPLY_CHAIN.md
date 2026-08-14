# Marketplace Trust and Supply Chain

Status: architecture contract.

## Scope

Applies to agents, skills, workflows, prompts, connectors, providers, models, templates, and SDK packages distributed through the CK-NEXUS marketplace or installed from external sources.

## Package identity

Every artifact has immutable content digest, publisher identity, artifact type, semantic version, manifest digest, source/provenance reference, dependency lock/bill of materials when applicable, license metadata, and signature/attestation references where available.

## Lifecycle

`DISCOVERED -> QUARANTINED -> VALIDATING -> CANDIDATE -> CANARY -> STABLE`

Any stage may transition to `REVOKED`. Installation never implies promotion.

## Admission gates

Admission can require schema validation, dependency closure, secret scan, malware/supply-chain checks, license/policy validation, contract tests, sandbox execution, security review, capability verification, provenance checks, and reproducible evidence.

## Permissions

Marketplace artifacts declare requested capabilities and permissions before installation. New permissions are not auto-granted during upgrades. Permission expansion requires policy evaluation and owner/admin approval as configured.

## Dependency integrity

Runtime resolution must use pinned/locked dependencies for release artifacts. Floating remote scripts/plugins are prohibited on production-impact paths unless explicitly governed and verified at invocation.

## Revocation

A revoked digest/version is removed from candidate selection immediately. Existing workflows referencing it fail closed or follow an explicitly approved compatibility/fallback policy. Evidence retains the historical digest and revocation reason.

## Trust score

Trust score is advisory only and cannot override hard policy. Inputs may include publisher verification, scan results, age/freshness, historical incidents, contract pass rate, provenance quality, reproducibility, and user/admin review.

## External AI knowledge

Public documentation or owner-provided outputs may create capability candidates. They do not import proprietary model weights, hidden prompts, inaccessible private skills, or unlicensed content. Knowledge ingestion preserves source/provenance and deduplicates semantically before promotion.
