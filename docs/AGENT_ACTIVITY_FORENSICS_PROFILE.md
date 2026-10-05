# Agent Activity Forensics Profile v1

Status: DEVELOPMENT DESIGN / NOT VERIFIED

## Objective
Reconstruct any consequential agent action without relying on model memory or raw prompt capture.

## Minimum event chain
intent -> agent -> model -> capability -> policy -> risk verdict -> lease -> approval -> AGNES -> tool -> target -> action -> result -> verifier -> evidence.

## Evidence fields
- event_id / trace_id / parent_event_id
- execution_id / parent_execution_id
- agent_id / model_id
- capability_id / tool_id / target_id
- policy_id / risk_verdict_id / lease_id / approval_id
- input_hash / output_hash
- runtime_id / host attestation reference
- timestamps and monotonic sequence
- decision / result / verifier_id
- evidence_id / provenance reference

## Privacy rule
Raw prompts, credentials, tokens and sensitive tool payloads are NOT default evidence. Store controlled references and cryptographic hashes where possible. Redaction happens before telemetry leaves the execution boundary.

## Delegation rule
Every delegated action must preserve parent_execution_id and authority attenuation. A child agent cannot gain authority merely because its parent had broader authority.

## Verification rule
Forensics evidence is not proof of correctness. It proves attributable execution history. Correctness still requires an independent verifier.
