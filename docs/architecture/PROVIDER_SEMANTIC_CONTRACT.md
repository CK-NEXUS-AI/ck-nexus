# Provider Semantic Contract

Status: architecture contract. Provider-specific SDK behavior is normalized behind this contract.

## Principle

Providers are replaceable implementations of semantic capabilities. CK-NEXUS must not assume that similarly named provider features have identical semantics.

## Required provider interface

A provider plugin declares:

- plugin ID and semantic version;
- capability manifest;
- supported input/output modalities;
- structured-output guarantees;
- tool/function calling semantics;
- streaming semantics;
- citation/grounding semantics;
- context/token limits as observations, not permanent constants;
- cost/quota observations;
- data handling and regional constraints;
- cancellation/timeout behavior;
- retry safety classification;
- health probe and freshness policy.

Runtime methods conceptually include `capabilities`, `health`, `invoke`, `stream`, `estimate_cost`, and `normalize_error`.

## Normalized request envelope

A request contains task/correlation IDs, semantic capability, content parts, requested output contract, tool grants, safety/policy context reference, budget, deadline, tenant, data classification, and evidence requirements. Raw credentials are forbidden.

## Normalized response envelope

A response contains provider/implementation identity, model observation, output parts, structured result when requested, tool-call proposals, citations/grounding metadata when available, usage observation, latency, finish reason, provider request ID if safe to retain, and normalization warnings.

## Tool calls

Provider-emitted tool calls are proposals only. They never directly perform impactful CK-NEXUS side effects. Proposed calls return to Trust + AGNES for authorization, idempotency, execution, verification, and evidence.

## Structured output

A provider claiming structured output must state the guarantee level: `best_effort`, `schema_checked_provider_side`, or `schema_constrained`. CK-NEXUS validates locally regardless for high-impact paths.

## Citations and grounding

Citation support is represented as semantic metadata with source identifiers, spans/claims when available, retrieval timestamp, and verification state. A provider's `citation` field is not automatically trusted as grounded evidence.

## Retry semantics

Each operation declares one of `safe`, `safe_with_idempotency_key`, `unsafe`, or `unknown`. Unknown is treated as unsafe for external side effects.

## Compatibility

Provider adapters may evolve independently, but contract breaking changes require a new major adapter contract version and registry compatibility evaluation. The orchestrator only consumes the normalized interface.
