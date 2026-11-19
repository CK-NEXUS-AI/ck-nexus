# Universal AI Adapter Contract v1.0

Status: DESIGNED / DEVELOPMENT

## Canonical envelope
intent_id, execution_id, agent_id, model_id, capability_id, policy_id, risk_verdict_id, authorization/lease_id, approval_id when required, path_id, alternative_of when fallback is used, tool_id, target_id, runtime_id, verifier_id, evidence_id, parent_execution_id for delegated work, status.

## Requirements
1. Preserve native identifiers.
2. Report missing fields; never fabricate them.
3. Map native statuses to canonical status vocabulary.
4. Record tool/runtime substitutions as alternative paths.
5. Keep external side effects inside capability/policy boundaries.
6. Make evidence durable enough for independent verification.
7. Redact sensitive telemetry before leaving the permitted boundary.
8. Fail closed when required governance fields are missing.
9. Read-only discovery may continue when an effectful path is blocked, if policy permits.
10. The verifier evaluates evidence and behavior, not the brand of tool.

## Conformance
CONFORMANT-DESIGN = mapping documented.
CONFORMANT-IMPLEMENTED = adapter exists.
CONFORMANT-EXECUTED = adapter has run.
CONFORMANT-VERIFIED = independent evidence validates behavior.
CONFORMANT-PRODUCTION = production-specific gates pass.
No conformance level may be claimed without evidence.