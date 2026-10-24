# UNIVERSAL AI CONFORMANCE MATRIX V1

Status: DEVELOPMENT / IMPLEMENTED ON FEATURE BRANCH / NOT VERIFIED

## Purpose

Map model, agent, protocol, orchestration, and runtime integrations to one CK-NEXUS governance contract without making any provider the authority.

Canonical rule:

HUMAN INTENT -> AGENT IDENTITY -> CAPABILITY -> RISK VERDICT -> LEASE/AUTHORIZATION -> POLICY -> PATH -> EXECUTION -> VERIFICATION -> EVIDENCE -> CANONICAL STATUS

## Conformance dimensions

| Dimension | Required control | Minimum evidence |
|---|---|---|
| Identity | Stable agent identity and proof | identity_id + proof/reference |
| Capability | Explicit capability scope | capability_id + scope |
| Authorization | Short-lived lease/authorization | lease_id + validity |
| Policy | Central policy decision | policy_id + decision |
| Risk | Pre-execution risk verdict | risk_verdict_id + decision |
| Approval | Human approval where required | approval_id |
| Path | Primary or declared alternative | path_id + alternative_of |
| Execution | Governed execution boundary | execution_id + runtime/tool |
| Verification | Independent verification | verifier_id + result |
| Evidence | Durable evidence record | evidence_id + hashes |
| Delegation | Parent/child provenance | parent_execution_id |
| Status | Canonical lifecycle state | status + evidence basis |

## Integration matrix

| Integration | Role | Authority allowed? | Required adapter boundary | Primary evidence | Main failure mode to test |
|---|---|---:|---|---|---|
| GPT | Model / proposer | NO | proposal envelope -> Policy Kernel | proposal_id, intent_id | model attempts authority |
| OpenCode | Coding agent / executor client | NO | agent identity + capability + lease | execution/evidence IDs | repo mutation without authorization |
| Claude | Model / agent client | NO | same universal envelope | execution/evidence IDs | tool use outside declared scope |
| OpenClaw | Agent runtime / tool orchestrator | NO | gateway -> policy/execution boundary | runtime_id + execution_id | tool escalation / unbounded autonomy |
| n8n | Workflow/orchestration runtime | NO | workflow node -> governed tool boundary | workflow/execution ID | credential or external write bypass |
| MCP | Tool protocol | NO | server/tool identity + per-tool policy | tool_id + execution_id | confused deputy / tool overreach |
| Generic Agent | Agent implementation | NO | adapter contract | agent_id + execution_id | missing identity/provenance |
| Generic Runtime | Execution environment | NO | runtime binding + sandbox | runtime_id + evidence_id | host/blast-radius escape |

## Mandatory negative gates

Every conforming adapter must demonstrate rejection for at least:

1. missing agent identity
2. invalid identity proof
3. missing capability
4. capability outside lease
5. expired lease
6. revoked lease
7. risk verdict mismatch
8. blocking risk decision
9. approval required without approval
10. missing policy
11. missing runtime
12. missing verifier
13. missing evidence requirement
14. tool/target mismatch
15. delegated child without parent execution
16. child capability escalation
17. unauthorized production mutation

The adapter test must exercise the real execution boundary, not only a validator in isolation:

invalid context -> adapter/dispatcher -> BLOCKED -> executor call count = 0

## Alternative-path conformance

An alternative is valid only if it preserves or strengthens:

- identity
- capability scope
- authorization/lease
- policy decision
- risk constraints
- required approval
- isolation
- verification
- evidence
- provenance

A failed tool is a BLOCK_PATH, not automatically a BLOCK_TASK.

## Evidence levels

- E0: intent/proposal only
- E1: policy/authorization evidence
- E2: execution evidence
- E3: independent verification
- E4: durable provenance/evidence chain
- E5: release/runtime evidence

E-level claims must never be promoted beyond the evidence actually recorded.

## Canonical status

DESIGNED != IMPLEMENTED != EXECUTED != VERIFIED != PRODUCTION

Production status requires production-specific evidence. CI success, static analysis, source inspection, or a feature-branch test cannot by itself establish production status.

## Audit verdict

Current matrix: DESIGNED/IMPLEMENTED on the Universal Standard feature branch.

Provider conformance: NOT VERIFIED.

This document does not promote Q10, Q11, Q12, merge, or production status.
