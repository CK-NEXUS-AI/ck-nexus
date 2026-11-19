# CK-NEXUS AI System Inventory X1

Status: DEVELOPMENT / PRE-ASSESSMENT
Last reviewed: 2026-09-05

This inventory is an assessor-preparation artifact. It records known AI-related components and explicitly marks items that still require verification.

## Inventory rules

Each AI component must have:
- component/system name
- owner
- intended use
- model/provider class
- data handled
- tool/capability access
- autonomy level
- human oversight
- security boundaries
- known limitations
- monitoring/evidence
- disable/rollback path
- verification state

## Current inventory

| ID | Component | Intended use | Provider/model state | Tool/capability access | Human oversight | Current state |
|---|---|---|---|---|---|---|
| AI-01 | AGNES execution/orchestration layer | governed planning and capability execution | provider-agnostic / runtime-dependent | registered executors only; sandboxed execution path where enabled | required by policy for high-risk paths | IMPLEMENTED / NOT_VERIFIED |
| AI-02 | AI Team / Universal System | specialist routing, planning, model/tool coordination | runtime/provider dependent | development, security and integration capabilities subject to policy | required for authority-sensitive decisions | IMPLEMENTED / NOT_VERIFIED |
| AI-03 | Auto Model Router | choose model/provider based on capability, cost, latency, quota and policy risk | dynamic provider selection | routing only; must not bypass credential/policy boundary | operational review required | IMPLEMENTED / NOT_VERIFIED |
| AI-04 | Council / multi-agent decision layer | multi-agent arbitration and safety veto | multi-agent / provider dependent | governed capability authority | close/uncertain decisions fail to human review | IMPLEMENTED / NOT_VERIFIED |
| AI-05 | Connector Fabric | connect MCP/OpenAPI/external tools under controlled policy | external tool/provider dependent | read/write/destructive risk classes | high-risk activation requires authorization | IMPLEMENTED / NOT_VERIFIED |
| AI-06 | Credential / Provider Manager | select and broker provider credentials without exposing raw secrets | provider registry | credential leasing and provider routing | admin/owner authority for sensitive changes | IMPLEMENTED / NOT_VERIFIED |
| AI-07 | Evidence / Verification layer | bind claims and execution results to evidence | non-generative authority layer | evidence read/write under controlled paths | independent human review required for final authority | IMPLEMENTED / NOT_VERIFIED |
| AI-08 | External LLM / AI providers | inference for specialist or agent tasks | exact active providers TO_VERIFY | network/API access through configured connectors/providers | governed by policy and routing | TO_VERIFY |
| AI-09 | Local inference runtime | private/offline inference where available | exact active runtime/model TO_VERIFY | local compute only when configured | operator oversight | TO_VERIFY |

## Known source evidence in repository

Existing implementation/security documents already provide relevant evidence and should be reused rather than duplicated:
- `docs/CK_NEXUS_UNIFIED_ARCHITECTURE.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE1_SECURITY_BASELINE.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE1_VALIDATION.md`
- `docs/AGNES_EXECUTION_KERNEL_PHASE2_ISOLATED_SANDBOX.md`
- `docs/R24_COUNCIL_CAPABILITY_AUTHORITY.md`
- `docs/R28_UNIVERSAL_AUTO_CONNECTOR_FABRIC.md`
- `creator_app/credentials/__init__.py`
- `creator_app/credentials/ai_provider_manager.py`

## Gaps to close before external assessment

- [ ] Confirm exact active model/provider inventory from runtime evidence
- [ ] Record data classes handled by each component
- [ ] Record retention and privacy behavior per provider
- [ ] Record exact tool permissions per agent/system
- [ ] Record autonomy level and human-approval threshold
- [ ] Record monitoring metrics and incident triggers
- [ ] Record disable/rollback procedure
- [ ] Record provider change-control process
- [ ] Record model evaluation and regression process
- [ ] Bind each material AI risk to the risk register

No component may be labeled VERIFIED solely because it appears in this inventory.
