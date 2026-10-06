# CK-NEXUS OMNI Control Plane — Architecture v2

Status: DEVELOPMENT DESIGN / NOT PRODUCTION
Date: 2026-10-06

## Evidence law
- NO EVIDENCE -> NO CLAIM
- NO EXECUTION EVIDENCE -> NO VERIFIED
- NO VERIFIED -> NO PASS
- NO PASS -> NO DONE
- NO PRODUCTION EVIDENCE -> NO PRODUCTION

## Authority boundary
GPT/model = proposer only.
Policy Kernel = authority.
Risk Verdict = pre-execution decision point.
AGNES = execution safety boundary.
Execution Gateway = effectful executor.
Verifier = independent checker.
Evidence Fabric = immutable-ish provenance/evidence layer.

## Canonical execution chain
Human Intent -> Agent Identity -> Capability -> Policy -> Risk Verdict -> Lease -> Approval -> AGNES -> Execution Gateway -> Tool/Runtime -> Verification -> Evidence -> Memory -> Recovery/Learning.

## Required action record
Every consequential action MUST bind:
- execution_id
- intent_id
- agent_id
- model_id
- capability_id
- policy_id
- risk_verdict_id
- lease_id
- approval_id when required
- tool_id
- target_id
- input_hash
- output_hash
- runtime_id
- verifier_id
- evidence_id
- parent_execution_id for delegated work

## Fail closed
Missing identity, capability, policy, risk verdict, lease, approval, sandbox, verifier, or evidence requirement => DENY or REQUIRE_APPROVAL according to policy; never silently downgrade to unrestricted execution.

## Design priorities
1. Least agency / least privilege
2. Short-lived capability leases
3. Action-level authorization
4. Pre-execution risk evaluation
5. Isolation and blast-radius limits
6. Redaction-first telemetry
7. Independent verification
8. Recovery before promotion
9. Full delegation provenance
10. Human approval for exceptional/high-risk mutation

## Research crosswalk candidates
- NIST_AGENT_ID_AUTHZ_CROSSWALK_V2
- A2A_GATEWAY_CONFORMANCE_PROFILE_V2
- OTEL_GENAI_REDACTED_ADAPTER_V2
- THAI_AI_EIA_REDTEAM_CROSSWALK_V2
- PRE_EXECUTION_RISK_VERDICT_PROFILE
- AGENT_ACTIVITY_FORENSICS_PROFILE
- DELEGATION_CHAIN_NEGATIVE_TESTS

These are design/test profiles until local implementation and independent verification exist.
