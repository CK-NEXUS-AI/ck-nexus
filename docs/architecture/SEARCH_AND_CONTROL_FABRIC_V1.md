# CK-NEXUS Search & Control Fabric v1

**Status:** IMPLEMENTED CONTRACT / TESTED LOCALLY / NOT CONNECTED TO LIVE SEARCH OR CONTROL PROVIDERS.

## Purpose

Provide a shared contract for discovering external capabilities and describing bounded
actions across websites, APIs, MCP servers, cloud platforms, CMSs and communication channels.
This is a provenance and policy boundary, not a crawler, agent executor or new authority plane.

## Discovery provenance

Every accepted discovery source records:
- stable source ID and HTTPS URL;
- publisher, retrieval timestamp, optional version and content type;
- SHA-256 of the retrieved source artifact;
- trust classification and explicit rights basis/license.

UNKNOWN rights or unverified publisher trust remains DISCOVERY_ONLY. Stale sources are
classified separately. Fetched instructions are always untrusted data, including official
documentation. Discovery candidates are not installation or execution permission.

Rights bases are public_domain, open_license, user_authorized, provider_terms, and unknown.
Every known rights basis must include a stable rights_evidence_ref; open-license evidence
must also name the license. The contract stores provenance metadata, not copied page bodies
or credentials.

## Control action contract

Each action declares its connector, exact action ID, required scopes, risk tier, maximum
timeout, evidence types and rollback capability.

Risk tiers:
- read: bounded observation;
- plan: planning only;
- sandbox_write: isolated reversible work;
- controlled_write: externally visible changes;
- destructive: deletion, revocation or irreversible effects.

Every action, including read-only actions, requires an injected trusted grant verifier.
The verifier must validate and consume a one-time CK-NEXUS Core grant bound to the exact
authenticated principal, connector, action, scopes and timeout. Write actions additionally
require an idempotency key and an approval reference. Destructive actions also require a
separate Owner approval reference. A principal ID or scope string supplied by an untrusted
caller is not authentication evidence.

This module never executes actions. ControlDecision.execution_performed is always false
and authority_level remains NONE; actual connector execution remains behind the existing
Connector Fabric and CK-NEXUS Core/L3 authorization path. A caller-provided boolean is not
a grant verifier.

## Integration boundary

- Search providers and crawlers are not added by this contract.
- MCP/OpenAPI connector discovery continues through creator_app/connector_fabric.
- Channel ingress continues through creator_app/channel_fabric and resolves identities
  before Brain planning.
- n8n remains a workflow plane, not an authority or Q10 judge.
- No auto-install, credential creation, write activation, deployment or Q10 status change
  is enabled by this module.

## Deferred live integrations

Search provider adapters, API documentation ingestion, durable discovery storage, provider
license verification, action registry persistence, and end-to-end channel-to-control
execution remain separate implementation and verification tasks.
