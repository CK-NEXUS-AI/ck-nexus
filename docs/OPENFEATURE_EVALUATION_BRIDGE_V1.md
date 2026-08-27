# CK-NEXUS OpenFeature Evaluation Bridge v1

Status: Development/Shadow candidate. `MEASURED_NOT_VERIFIED` ceiling until exact-head CI and independent verification.

## Standard baseline

OpenFeature specification v0.9.0 stabilizes the evaluation and provider sections and hardens hooks, events, and evaluation context.

This bridge implements only the provider-neutral evaluation boundary needed by CK-NEXUS:

- typed boolean, string, number, and object resolution;
- provider metadata name;
- evaluation context pass-through;
- resolution reason / variant / error code;
- No-op provider returning the supplied default;
- provider errors and type mismatches fail safely to the supplied default;
- deterministic evidence digest for the evaluation projection.

It is **not** a full OpenFeature SDK conformance claim. It does not implement the global API singleton, provider lifecycle/events, hooks, tracking, multi-provider composition, a remote provider, or a flag management/control plane.

## CK-NEXUS authority boundary

Feature flags are behavior-selection inputs only. They are never permissions or evidence upgrades.

Every `FlagEvaluationDetails` object hard-codes:

- `authority = CK-NEXUS`
- `permission_granted = false`
- `verification_upgrade_allowed = false`
- `production_mutation_allowed = false`

Therefore a provider may resolve a flag named `production_mutation` to `true`, but that value cannot authorize Production mutation. Any privileged action must still pass the CK Governor, approvals, Verification Plane, and release gates.

## Failure behavior

Normal provider success returns the provider value when it matches the requested type.

Provider exception, provider-declared error, or type mismatch returns the caller-supplied default. The evaluation call records the error code in details and does not use a provider failure as authority.

## Deliberate omissions

No custom flag database is introduced. No network calls, credentials, vendor SDK, polling worker, external write, deployment, merge, or Production mutation is performed by this bridge.

Future provider integrations should adapt an external OpenFeature-compatible provider behind the `FeatureProvider` contract rather than creating a second CK-NEXUS flag authority.
