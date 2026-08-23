# AGNES Frontier Model Governance V1

Status: Development-only. This document does not change release/production closure.

## Purpose

Extend CK-NEXUS / AGNES for frontier, local, multimodal, long-context and safety-modified models without transferring authority from CK-NEXUS to any model or provider.

## New capability contracts

- VIDEO
- LONG_CONTEXT
- THINKING_CONTROL
- THINKING_CONTINUITY
- AGENTIC_EXECUTION
- ENVIRONMENT_FEEDBACK
- LOCAL_MULTIMODAL
- QUANTIZED_RUNTIME
- RED_TEAM_MODEL
- MODEL_ATTESTATION

## Identity separation

Model, provider and runtime identities are distinct:

- model_id: model/weight identity
- provider_id: serving/provider identity
- runtime_id: execution runtime identity

## Provenance

ModelDescriptor can bind model repository, revision SHA, weight digest, base model, modifier, quantization, license and attestation state.

Attestation states are CLAIMED, MEASURED and VERIFIED. Production-lane routing requires VERIFIED plus revision_sha and weight_digest.

## Capability attestation

Capability claims are not treated as verification. `attest_capabilities()` accepts explicit per-capability checks and produces a deterministic digest.

- no passing checks -> CLAIMED
- partial passing checks -> MEASURED
- every claimed capability passing with evidence IDs -> VERIFIED

A behavioral fingerprint is also bound to provider/model/runtime identity, revision, weight digest, quantization and measured scalar metrics. A changed revision or weight identity therefore produces a different fingerprint and should invalidate stale behavioral evidence.

## Risk classes

- STANDARD
- EXPERIMENTAL
- RED_TEAM_ONLY
- SAFETY_MODIFIED
- UNTRUSTED_WEIGHTS

Known safety-removal identity markers such as abliterated/obliterated/uncensored are conservatively elevated to SAFETY_MODIFIED.

Restricted models are denied from development/evaluation/production routing and can enter only the RED_TEAM lane, where quarantine remains required.

## OpenAI-compatible provider boundary

`OpenAICompatibleProviderAdapter` provides a provider-neutral boundary for OpenAI-compatible runtimes such as remote hosted services or local compatible servers.

Security properties:

- remote base URLs require HTTPS
- embedded URL credentials are rejected
- query/fragment credential patterns are rejected
- local HTTP requires explicit loopback-only opt-in
- model/provider/runtime identities must match the registered endpoint
- unknown model IDs are rejected
- the adapter carries only a `credential_ref`; raw secret material is resolved behind the injected transport / Credential Broker boundary

The adapter does not read environment variables, API keys or secret stores directly.

## Qwen3.8 / OBLITERATED handling

The OBLITERATUS/Qwen3.8-27B-OBLITERATED family is not registered as a production model by this change. If introduced later, it must be classified through the governance layer and restricted to the RED_TEAM lane unless independently re-attested under a different approved policy.

No Hugging Face, Featherless or other provider credential is stored in this repository by this change.

## Reasoning continuity

The gateway can describe reasoning effort and whether a provider supports preserved reasoning context. CK-NEXUS must not store private chain-of-thought as evidence. Evidence should contain public rationale/decision summaries and digests only.

## Production boundary

This development capability is independent from Q10/Q11/Q12 and cannot promote production eligibility. Production closure remains governed by the canonical production evidence chain.
