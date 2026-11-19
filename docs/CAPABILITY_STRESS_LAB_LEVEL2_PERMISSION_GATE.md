# CK-NEXUS Capability Stress Lab — Level 2 Permission Gate

Status: Development / Post-P0 / Not Production Evidence

## Objective

Level 2 proves a core CK-NEXUS invariant:

> Connector availability, installed provider permissions, repository admin rights, and schema discovery are observations only. They are never execution or mutation authority.

This gate specifically addresses broad provider permission surfaces such as a connected GitHub account reporting admin/push rights. The provider may expose those permissions, but CK-NEXUS must independently decide whether a non-read capability is allowed to become model-visible and must independently authorize every later invocation.

## Runtime contract

The Connector Fabric now separates three states of trust:

1. **Discovery trust** — a connector endpoint and tool schema were verified.
2. **Activation authority** — a separate CK-NEXUS grant is required before write/destructive tools can become active and model-visible.
3. **Execution authority** — every tool invocation still requires its own policy decision and one-time execution grant.

A successful write activation does not grant tool execution.

## Fail-closed rules

- Read-only activation remains the default.
- `allow_write=True` fails when no trusted activation authorizer is configured.
- Unknown-risk tools hard-block write activation before any authorizer is consulted.
- A trusted activation authorizer must return an explicit allow decision.
- The Capability Authority adapter binds activation to connector identity, verified schema hash, tool counts, task/evidence context, and a one-time grant.
- Activation evidence records approval or denial without storing provider credentials or raw access tokens.
- Per-tool execution remains governed by the existing Tool Authorizer.

## Stress-Lab acceptance cases

- A connector containing read + write tools cannot enter `ACTIVE_WRITE` with the default configuration.
- The same connector can enter `ACTIVE_READ_ONLY`, exposing only read-only tools.
- A separately approved write activation can expose verified write tools, but invocation still fails without a separate tool execution grant.
- A connector containing any `UNKNOWN` risk tool cannot enter `ACTIVE_WRITE`, even if an injected activation authorizer would otherwise approve it.

## Evidence classification

This implementation and its CI results are development evidence for Capability Stress Lab Level 2. They do not satisfy Q10, Q11, Q12, production closure, or Final Production Package requirements.

Production status remains NO-GO until the independent production closure sequence passes.
