# CK-NEXUS Layered Monorepo Target Architecture

Status: TARGET_ARCHITECTURE / NON-CANONICAL

Baseline canonical source: `45fde79c717b09f8675645aa541a5834ebd4f433`

This document defines the target repository layout. It does not promote any release gate and must not be treated as evidence that the migration is complete.

## Principles

1. One responsibility per top-level layer.
2. No duplicate ownership for governance, services, evidence, provider, or integration concerns.
3. Provider-neutral core contracts. OpenAI, Anthropic, Gemini, local, and custom providers implement shared interfaces.
4. Integration credentials remain brokered; providers and connectors never own long-lived secrets directly.
5. AGNES is the only execution plane for side effects. Cognitive components propose; governance authorizes; AGNES executes; evidence records.
6. All high-impact operations are fail-closed and capability-bound.
7. Existing Q01-Q09 evidence remains authoritative for the current canonical tree only. Structural migration requires fresh evidence.

## Target layout

```text
ck-nexus/
├── apps/
│   ├── control-hub/
│   ├── admin-console/
│   ├── buyer-demo/
│   ├── api-gateway/
│   └── dashboard/
├── services/
│   ├── gateway/
│   ├── orchestrator/
│   ├── cognitive_fabric/
│   ├── cognitive_governor/
│   ├── consensus/
│   ├── planner/
│   ├── verifier/
│   ├── credential_broker/
│   ├── provider_registry/
│   ├── tool_registry/
│   ├── memory/
│   ├── knowledge/
│   ├── evidence_service/
│   ├── audit_service/
│   └── integration_service/
├── agnes/
│   ├── runtime/
│   ├── planner/
│   ├── dispatcher/
│   ├── executor/
│   ├── scheduler/
│   ├── automation/
│   ├── workflow/
│   ├── recovery/
│   ├── checkpoints/
│   ├── skills/
│   ├── ledger/
│   └── execution/
├── intelligence/
│   ├── intent_graph/
│   ├── task_dag/
│   ├── reasoning/
│   ├── capability_router/
│   ├── model_router/
│   ├── conflict_resolver/
│   ├── learning/
│   └── planner/
├── providers/
│   ├── common/
│   ├── openai/
│   ├── anthropic/
│   ├── gemini/
│   ├── xai/
│   ├── deepseek/
│   ├── mistral/
│   ├── qwen/
│   ├── llama/
│   ├── ollama/
│   └── custom/
├── integrations/
│   ├── github/
│   ├── gmail/
│   ├── google/
│   ├── outlook/
│   ├── slack/
│   ├── notion/
│   ├── wix/
│   ├── base44/
│   ├── cloudflare/
│   ├── openclaw/
│   ├── replit/
│   ├── mcp/
│   ├── a2a/
│   ├── webhooks/
│   └── connectors/
├── governance/
│   ├── policies/
│   ├── authority/
│   ├── approvals/
│   ├── risk/
│   ├── quotas/
│   ├── compliance/
│   └── kill_switch/
├── contracts/
├── schemas/
├── config/
├── data/
├── observability/
├── evidence/
├── api/
├── cli/
├── scripts/
├── tests/
├── docs/
└── releases/
```

## Shared provider interface

Every model provider must implement one common contract with normalized request/response envelopes, capability metadata, health, cost/quota metadata, and policy/data-boundary declarations. Provider implementations are replaceable adapters; orchestration must not depend on vendor-specific SDK objects.

Required logical operations:

- `capabilities()`
- `health()`
- `generate()`
- `stream()` when supported
- `embed()` when supported
- `tool_support()`
- `usage_snapshot()`

Provider routing must honor policy, budget, data residency, free-only mode, health, and historical quality. It must never rotate accounts or credentials to evade quotas.

## Connector fabric

Connectors use a shared registry and normalized lifecycle:

`DISCOVERED -> OWNER_AUTHORIZED -> HEALTHY -> DEGRADED -> REAUTH_REQUIRED -> DISABLED`

Credentials are references/leases issued by Credential Broker. Gmail may be used as a notification or coordination hub, but Gmail must not become an implicit trust root for unrelated connector permissions.

## Execution boundary

All side effects flow through:

`Intent -> Cognitive Governor -> Policy/Risk -> Capability Grant -> AGNES Dispatcher -> Adapter -> Evidence/Audit`

No model/provider/integration is permitted to bypass AGNES for high-impact mutation.

## Evidence boundary

Evidence is immutable and source-bound. A structural move, import-path change, dependency change, or runtime behavior change invalidates exact-tree evidence and requires regeneration. Historical evidence must remain available as lineage but cannot be relabeled as current.
