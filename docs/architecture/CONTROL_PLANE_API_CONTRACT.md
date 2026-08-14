# Control Plane API Contract

Status: architecture contract. No runtime authority is granted by this document.

## Purpose

The Unified Command Center is a client of CK-NEXUS Control Plane APIs. It never talks directly to provider SDKs, credential stores, production infrastructure, or external connectors for consequential operations.

## API separation

Read plane:

- health/status
- capability registry
- connector/provider state
- tasks/executions
- approvals
- evidence/gates
- incidents/alerts
- observability summaries
- cost/quota observations

Command plane:

- submit intent
- pause/resume/cancel task
- request approval
- approve/reject a specific request
- request reconnect/disconnect/permission change
- request recovery/compensation
- request marketplace install/promote/revoke

Command endpoints create commands/requests; they do not imply the side effect already happened.

## Command lifecycle

`RECEIVED -> VALIDATED -> POLICY_EVALUATED -> PENDING_APPROVAL|AUTHORIZED -> DISPATCHED -> VERIFIED|FAILED|BLOCKED|UNKNOWN`

A command response returns command ID and current state. HTTP success only means the control-plane request was accepted/processed, not that the external business action committed.

## Idempotency

All command-plane POST operations require a client request/idempotency key. The server binds it to authenticated principal, tenant, command type, target, and request hash. Reuse with a different semantic request is rejected.

## Concurrency

Mutable control objects expose version/ETag or equivalent optimistic concurrency. Approvals, policy edits, task controls, and connector permission changes reject stale writes rather than last-writer-wins silently.

## Authentication and authorization

Authentication identifies principal/session/tenant. Authorization occurs server-side for every request. UI hiding is never authorization. High-impact commands additionally require policy authority and, when configured, explicit approval.

## Response safety

Control-plane responses never return raw API keys, refresh tokens, private keys, credential payloads, or secret environment values. Credential state is redacted to provider, credential class, lease state, expiry/freshness, and fingerprint/reference where safe.

## Event updates

Clients may use polling or event streams for status. Events are hints; the authoritative current object is retrieved by ID/version. Reconnect after gaps uses cursor/replay where supported.

## Audit

Every command-plane mutation records actor, tenant, command, target, policy/approval refs, timestamp, request hash, resulting state, and evidence refs. Security-sensitive reads may also be audited.

## API compatibility

Public control-plane contracts are versioned independently from provider adapters. Breaking changes require a new major API version or explicit negotiated compatibility profile.
