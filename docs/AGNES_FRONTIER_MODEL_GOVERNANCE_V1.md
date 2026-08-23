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

## Risk classes

- STANDARD
- EXPERIMENTAL
- RED_TEAM_ONLY
- SAFETY_MODIFIED
- UNTRUSTED_WEIGHTS

Known safety-removal identity markers such as abliterated/obliterated/uncensored are conservatively elevated to SAFETY_MODIFIED.

Restricted models are denied from development/evaluation/production routing and can enter only the RED_TEAM lane, where quarantine remains required.

## Qwen3.8 / OBLITERATED handling

The OBLITERATUS/Qwen3.8-27B-OBLITERATED family is not registered as a production model by this change. If introduced later, it must be classified through the governance layer and restricted to the RED_TEAM lane unless independently re-attested under a different approved policy.

No Hugging Face, Featherless or other provider credential is stored in this repository by this change.

## Reasoning continuity

The gateway can describe reasoning effort and whether a provider supports preserved reasoning context. CK-NEXUS must not store private chain-of-thought as evidence. Evidence should contain public rationale/decision summaries and digests only.

## Production boundary

This development capability is independent from Q10/Q11/Q12 and cannot promote production eligibility. Production closure remains governed by the canonical production evidence chain.
