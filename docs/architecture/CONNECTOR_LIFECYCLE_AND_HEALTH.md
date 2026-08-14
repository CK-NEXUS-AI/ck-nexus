# Connector Lifecycle and Health Model

Status: architecture contract.

## Separate dimensions

Connector lifecycle, authorization, runtime health, and capability verification are separate fields. Do not collapse all of them into a single `connected=true` flag.

## Lifecycle

`DISCOVERED`, `CONFIGURED`, `CONNECTED`, `DEGRADED`, `REAUTH_REQUIRED`, `DISCONNECTED`, `QUARANTINED`, `REVOKED`, `UNAVAILABLE`.

## Authorization state

`NOT_CONFIGURED`, `CONSENT_REQUIRED`, `AUTHORIZED`, `SCOPE_INSUFFICIENT`, `EXPIRED`, `REVOKED`, `UNKNOWN`.

## Health state

`UNKNOWN`, `HEALTHY`, `DEGRADED`, `UNHEALTHY` with `observed_at`, `fresh_until`, probe method, latency and error class. Stale health is treated as unknown for eligibility.

## Capability verification

A connector may be authorized but a capability can still be unverified. Capability states include `DISCOVERED`, `CANDIDATE`, `VERIFIED`, `DISABLED`, `QUARANTINED`, `REVOKED`.

## Scope mapping

Provider-native OAuth scopes are retained as observations and mapped to semantic CK capabilities. Mapping is necessary but not sufficient; safe capability probes/contract tests verify behavior.

## Reauthentication

CK-NEXUS may detect reauth need and initiate an owner-facing consent flow, but cannot bypass provider consent. OAuth refresh may occur within the provider/credential broker contract. Raw tokens are never returned to the UI.

## Permission changes

Permission expansion is a distinct command. The requested complete scope set, semantic capability impact and risk delta are shown before consent. Scope reduction is allowed but may disable dependent workflows; impact analysis should be shown.

## Failover

Failover selects another already-authorized eligible connector/provider only. It never copies credentials between services or automatically signs up new accounts.

## Evidence

Each live observation records runtime/provider identity, account reference in redacted form, granted scopes, health freshness, source kind, normalized capabilities, validation state and evidence reference.
