# CK-NEXUS CANONICAL MASTER SOURCE
## Unified 5-Layer Architecture • R4–R8 Baseline • R9–R12 Execution Blueprint • Ω∞ / NEXUS-X CRANE Alignment

**Document role:** Canonical single-source blueprint. This file is intentionally self-contained so it can later be split into architecture docs, API contracts, schemas, configuration, runbooks, and implementation tickets without losing context.

**Current verified baseline:** CK-NEXUS R8 — Persistent Encrypted Credential Vault

- Branch: `r8-encrypted-vault`
- Commit: `ded79e08b930b5a6b733bcc658bfc9615d1b09a8`
- Baseline R7: `11b35ca94937b98264e996e9e22c5dea20d9ffb6`
- Release posture: **Development Candidate / Release Candidate / NO-GO**
- Verified non-billing regression reported in R8 identity: **95 PASS**
- AI001 live OpenAI production-path smoke: **BLOCKED / not executed in R8 slice**

**Important scope note:** The names **CK-NEXUS Ω∞** and **NEXUS-X CRANE** are used in this document as architectural overlays supplied in the project context. Their ideas are integrated where they match verified CK-NEXUS behavior (multi-agent orchestration, circuit breaker, fail-closed, canary/repair/rollback, learning loops). They are not independently claimed as separately verified artifacts unless their source packages are later attached and audited.

---

# 0. Executive Summary

CK-NEXUS is defined here as an autonomous, composable, secure-by-default operating system for AI-assisted work. It accepts requests from humans or systems, authenticates and authorizes them, retrieves context, selects a workflow pattern, plans, executes bounded actions through approved tools, verifies results, requests human approval where policy requires it, records audit evidence, learns from outcomes, and expands successful ideas into reusable knowledge and products.

The entire system is standardized into **five layers**:

```text
┌──────────────────────────────────────────────────────────────┐
│ L5  IDEA / CREATIVITY ENGINE                                │
│     idea expansion • frameworks • note graph • opportunity  │
├──────────────────────────────────────────────────────────────┤
│ L4  ORCHESTRATION / MULTI-AGENT LAYER                       │
│     lead orchestrator • patterns • council • guardrails     │
├──────────────────────────────────────────────────────────────┤
│ L3  API GATEWAY / CONTROL EDGE                              │
│     routing • auth • distributed rate-limit • BFF • audit   │
├──────────────────────────────────────────────────────────────┤
│ L2  CORE SERVICES                                           │
│     credential broker • provider router • email • billing   │
├──────────────────────────────────────────────────────────────┤
│ L1  DATA & INFRASTRUCTURE                                   │
│     postgres • redis • queue • encrypted vault • evidence   │
└──────────────────────────────────────────────────────────────┘
```

The canonical system flow is:

```text
Input
  → Gateway
  → Authenticate / Authorize
  → Intent Classification
  → Context Retrieval
  → Workflow Pattern Selection
  → Plan
  → Execute
  → Verify
  → Human Approval (when required)
  → Deliver
  → Audit / Observe
  → Learn
  → Idea Expansion / Reuse
```

The next development sequence is fixed as:

- **R9 — API Gateway + distributed Redis rate limiting**
- **R10 — Orchestration Pattern Library + Council integration**
- **R11 — Idea Engine + Knowledge Note Graph**
- **R12 — Staging Evidence Sprint and Production Gate closure**

R9–R11 add capability. **R12 supplies production evidence.** No capability release may override a missing staging gate.

---

# 1. Source Synthesis — What the Image Set Contributes

The attached infographic set contributes design patterns rather than production evidence. This blueprint extracts the useful concepts and maps them to CK-NEXUS without copying any one diagram literally.

## 1.1 Agentic workflow images

Core extracted pattern:

```text
Intake → Research → Plan → Execute → Review → Report → Feedback
```

CK-NEXUS mapping:

- Intake Agent → Request Intake / Intent layer
- Research Agent → Research & Analyst specialist
- Planner → Lead Orchestrator + Architect
- Execution Agent → Execution Controller, never advisory agent directly
- Reviewer → Security / QA / DevOps Reviewer
- Reporting Agent → Audit / Delivery / Learning Feedback

Key design rule: **agents advise and plan; controlled executors perform side effects.**

## 1.2 API gateway and system-design images

Useful concepts folded into R9:

- client/server boundaries
- DNS / HTTP / HTTPS / TCP fundamentals
- reverse proxy / gateway
- latency budgets
- REST API contracts
- database isolation
- caching
- horizontal scaling
- queues and asynchronous execution
- rate limiting
- idempotency
- observability
- load distribution

The system-design references reinforce that each new service must explicitly answer:

1. What can be cached and for how long?
2. Where does rate-limit state live?
3. What is the idempotency key?
4. Is the dependency synchronous or queued?
5. What are the availability/consistency trade-offs?
6. What is the timeout budget?
7. What happens when a dependency is unavailable?

## 1.3 React / JavaScript roadmap and cheat-sheet images

Useful frontend discipline:

- component ownership
- state isolation
- routing
- typed interfaces
- predictable effects
- cleanup for subscriptions/listeners
- API cancellation and timeout handling
- reusable UI primitives
- error/loading/empty states as first-class UI states
- no secrets in browser bundles

This becomes the frontend rulebook for CK-NEXUS Dashboard, Dev Team, Integration Hub and future Admin Console.

## 1.4 Python roadmap and higher-order-function images

Useful backend discipline:

- explicit functions and modules
- composition over monoliths
- higher-order wrappers for policy, retries, tracing and guardrails
- async I/O discipline
- structured exceptions
- package boundaries
- tests before release claims

## 1.5 Networking / CPU / infrastructure images

Useful infrastructure concepts:

- protocols are explicit contracts, not assumptions
- CPU/memory constraints matter for worker concurrency
- connection-oriented vs connectionless behavior matters for retries
- DNS and transport failures must be bounded by timeout/circuit breaker
- production readiness requires understanding resource pressure, not only passing unit tests

## 1.6 AI-tool / future-tech / AI-native-company images

Useful product concepts:

- AI should be a context and orchestration layer, not an isolated chatbot
- humans retain strategy, judgment, creativity and approval
- agents perform repeatable, well-bounded labor
- reusable context creates compounding value
- monetization comes from productized workflows, templates, managed knowledge and vertical solutions

## 1.7 Mind-map / idea-expansion images

Useful creativity concepts:

- questions branch into assumptions, risks, opportunities and next actions
- ideas should form a connected graph rather than a flat note list
- frameworks should be selected based on the problem rather than applied all at once

This becomes L5 Idea Engine.

## 1.8 Red-team / blue-team / ATT&CK-style images

Only the defensive design value is adopted:

- threat awareness
- abnormal credential behavior detection
- access control
- logging
- monitoring
- incident readiness
- recovery
- policy guardrails

No offensive execution capability is introduced by this blueprint.

---

# 2. R4–R8 Evolution and Current Ground Truth

This section preserves development lineage so future releases do not accidentally regress earlier protections.

| Release | Architectural contribution | Known identity / posture |
|---|---|---|
| R4 | Integration Hub, safe status endpoints, CI structure, model/config cleanup | commit `b47a95b0cfa858dae5a55d4092af827d84ca1799`, tag `v0.2.0-p0-rc.2` |
| R5 | Development Council with five advisory specialists | commit `dca89ffed25e421030ae3fb88717a80b39bb8141`, tag `v0.2.0-p0-rc.3` |
| R6 | Autonomy hardening: Mock/local-first provider router, bounded fallback, circuit breaker, fail-closed, live/ready health, repair/canary/rollback | commit `4603d45acdbde13491582c7a6f85570372035c86` |
| R7 | Credential Broker, Ollama/OpenAI adapters, Gmail OAuth, GitHub App flow, provider-router cutover into Council/CreatorRuntime | commit `11b35ca94937b98264e996e9e22c5dea20d9ffb6`, tag `v0.2.0-p0-rc.4` |
| R8 | Persistent Encrypted Credential Vault | commit `ded79e08b930b5a6b733bcc658bfc9615d1b09a8`, RC / NO-GO |

## 2.1 Capabilities that must not be lost

- secrets are never returned through status APIs
- provider selection is policy-driven
- OpenAI/Ollama/Mock are routed through controlled adapters
- Ollama network scope remains restricted by policy
- production behavior is fail-closed
- circuit breaker state influences provider availability
- health/live is distinct from health/ready
- repair/canary/rollback uses a state machine, not arbitrary self-modification
- Development Council remains advisory by default
- side effects are controlled by execution gates
- production claims require staging evidence

## 2.2 Current blockers inherited into R9–R12

- rate limiting suitable for horizontal scaling is not yet established as a cluster-wide guarantee
- live OpenAI AI001 production-path evidence is still missing at R8 baseline
- PostgreSQL concurrency evidence must be proven on production-like staging
- backup/restore evidence must be destructive and isolated, not a local-file simulation
- n8n audit must run for real in staging
- alert delivery must be proven, not inferred from logs
- clean-machine deployment must prove the release artifact is self-contained

---

# 3. Global System Invariants

These rules apply to every layer and every release.

## 3.1 Identity

Every request or execution must have:

- `tenant_id`
- `actor_id`
- `actor_type`
- `correlation_id`
- `request_id`
- `execution_id` when work begins
- authenticated claims or explicitly anonymous public policy

## 3.2 Authorization

Authentication at the gateway does not eliminate downstream authorization. Critical services validate:

- audience
- tenant
- permission
- resource scope
- policy version

## 3.3 Correlation and traceability

One correlation ID must be visible through:

```text
Gateway → Orchestrator → Service → Provider/Workflow → Audit → Alert/Report
```

## 3.4 Idempotency

Every side-effecting operation must define an idempotency strategy.

Minimum key form:

```text
tenant_id : operation_type : logical_resource_id : operation_version
```

Rules:

- key stored durably when external side effect matters
- duplicate request returns prior result or deterministic duplicate status
- retries cannot create duplicate external effects
- idempotency record has lifecycle and audit trail

## 3.5 Timeouts

Each network call has a timeout; each workflow has a total budget.

```text
request_budget
  ├─ auth_budget
  ├─ context_budget
  ├─ planning_budget
  ├─ execution_budget
  └─ delivery_budget
```

No unbounded retries.

## 3.6 Circuit breaker

States:

```text
CLOSED → OPEN → HALF_OPEN → CLOSED
                  └──────→ OPEN
```

The breaker is provider/service specific. Failure in one provider cannot invalidate all providers unless policy says no safe fallback exists.

## 3.7 Fail-closed

Sensitive actions default to deny/block when required policy dependencies are missing.

Fail-open is permitted only for explicitly classified non-sensitive read paths and must be documented per route.

## 3.8 Secret safety

- raw secret values never appear in status
- raw secret values never enter model prompts unless adapter-internal use is unavoidable and explicitly bounded
- browser never receives server credentials
- logs redact Authorization headers, cookies, tokens, private keys, refresh tokens and API keys
- application obtains scoped credential leases rather than direct vault dumps

## 3.9 Human approval

Approval must be independent of the agent requesting the action.

Approval is mandatory by default for:

- external outbound messages in new campaigns
- production deploy
- destructive data actions
- payment/billing mutations
- permission escalation
- irreversible publication

## 3.10 Auditability

Every important decision emits an immutable audit event with:

```json
{
  "event_id": "uuid",
  "correlation_id": "uuid",
  "execution_id": "uuid-or-null",
  "tenant_id": "tenant",
  "actor_id": "actor",
  "actor_type": "human|service|agent",
  "component": "gateway|orchestrator|service|provider|vault",
  "action": "string",
  "decision": "allow|deny|execute|skip|fail|block",
  "policy_version": "string",
  "status": "success|failure|blocked",
  "latency_ms": 0,
  "timestamp": "RFC3339"
}
```

---

# 4. Unified Five-Layer Architecture

# L1 — Data & Infrastructure

## 4.1 Responsibilities

- PostgreSQL durable transactional state
- Redis distributed coordination
- queues / async jobs
- encrypted secret storage
- immutable evidence artifacts
- backup and restore
- schema migration discipline

## 4.2 PostgreSQL domains

Suggested logical schemas:

```text
identity
workflow
knowledge
audit
integration
billing
email
idea
release_evidence
```

Core tables:

```text
workflow.executions
workflow.steps
workflow.idempotency_records
workflow.approvals
workflow.outbox
workflow.leases

audit.events

auth.service_identities

auth.permission_bindings

knowledge.nodes
knowledge.edges
knowledge.documents
knowledge.embeddings_metadata

idea.proposals
idea.framework_runs

release_evidence.runs
release_evidence.gates
```

## 4.3 Redis domains

Use namespaces:

```text
ratelimit:{policy}:{tenant}:{actor}:{route}
cache:{resource}:{version}:{key}
lock:{resource}
lease:{worker}:{job}
circuit:{provider}
nonce:{oauth_state}
```

Redis is not the system of record for durable business truth.

## 4.4 Queue contract

Minimum job envelope:

```json
{
  "job_id": "uuid",
  "tenant_id": "tenant",
  "correlation_id": "uuid",
  "execution_id": "uuid",
  "job_type": "string",
  "payload_ref": "opaque-reference",
  "attempt": 1,
  "max_attempts": 3,
  "not_before": "RFC3339",
  "idempotency_key": "string",
  "created_at": "RFC3339"
}
```

The payload should reference protected storage when sensitive rather than embedding secrets in queue messages.

## 4.5 Encrypted credential vault

Target behavior after R8:

```text
Secret Material
  → Encrypt with managed root/key hierarchy
  → Store encrypted record
  → Credential Broker validates consumer + purpose
  → Scoped lease created
  → Adapter consumes lease
  → Lease expires/revokes
  → Audit event records metadata only
```

Record metadata:

```json
{
  "credential_id": "uuid",
  "provider": "openai|gmail|github|slack|n8n|other",
  "tenant_id": "tenant",
  "secret_class": "api_key|refresh_token|private_key|access_token",
  "version": 3,
  "status": "active|rotating|revoked|expired",
  "created_at": "RFC3339",
  "expires_at": null,
  "last_rotated_at": "RFC3339"
}
```

Never expose ciphertext or secret value through public status.

## 4.6 Evidence storage

Release evidence must be outside the source tree or in a dedicated immutable mount.

Recommended path:

```text
/var/lib/ck-nexus/evidence/<run_id>/
```

Files include:

```text
identity.json
gate-EMAIL001.json
...
gate-OPS001.json
final-decision.json
raw/
```

---

# L2 — Core Services

## 4.7 Service boundaries

### Credential Service

Responsibilities:

- authorize credential lease
- lease by consumer and purpose
- expiry/revocation
- rotation metadata
- audit

No public raw-secret endpoint exists.

### Provider Service

Adapters:

- Mock
- Ollama local/allowed scope
- OpenAI
- future providers via same interface

Canonical adapter interface:

```python
class ProviderAdapter(Protocol):
    name: str

    async def health(self) -> ProviderHealth: ...
    async def execute(self, request: ProviderRequest, ctx: ExecutionContext) -> ProviderResult: ...
```

Router decision factors:

- environment
- policy
- capability
- model class
- latency
- cost ceiling
- circuit state
- tenant permission

### Email Service

Must support:

- inbound normalization
- dedup
- outbox
- bounded retry
- provider request IDs
- attachment quarantine
- loop prevention
- OAuth connector

### Billing Service

Minimum rules:

- transactional boundary
- idempotent mutation
- immutable ledger/audit reference
- no billing mutation directly from advisory agents

### Integration Service

Connectors include:

- Gmail OAuth
- GitHub App
- Slack
- Google Drive
- n8n
- additional services through plugin/connector boundaries

### Audit Service

Normalizes events and writes durable audit records.

## 4.8 Internal service contract

Every internal request includes an identity envelope:

```json
{
  "tenant_id": "t1",
  "actor_id": "u1",
  "actor_type": "human",
  "correlation_id": "c1",
  "request_id": "r1",
  "permissions": ["workflow.run"],
  "audience": "workflow-service",
  "policy_version": "2026-08-09.1"
}
```

---

# L3 — API Gateway / R9

# 5. R9 Objective

Create a single external policy edge that solves distributed rate limiting and normalizes routing/auth/audit without becoming a single trust bypass.

## 5.1 Recommended implementation

Start with FastAPI to reuse CK-NEXUS Python tooling and test patterns. Keep contracts proxy-neutral so Kong/Envoy can be introduced later if operational requirements justify it.

Target package:

```text
gateway/
  __init__.py
  app.py
  config.py
  auth.py
  identity.py
  correlation.py
  rate_limit.py
  routing.py
  proxy.py
  bff.py
  cache.py
  timeout.py
  audit.py
  health.py
  errors.py
  tests/
```

## 5.2 Middleware order

Canonical order:

```text
Request
 → request-size guard
 → correlation ID
 → trusted proxy parsing
 → authentication
 → authorization pre-check
 → distributed rate limit
 → route policy
 → timeout budget
 → upstream execution
 → response normalization
 → audit emission
```

## 5.3 Route policy model

```yaml
routes:
  - id: creator.run
    path: /api/v1/creator/run
    methods: [POST]
    upstream: creator-runtime
    audience: creator-runtime
    permissions: [creator.run]
    rate_limit_policy: interactive-standard
    timeout_ms: 45000
    cache: false
    retry: idempotency-required
    side_effect: true
    fail_mode: closed
```

## 5.4 Distributed rate limiter

### Required property

The request budget must be shared across every gateway instance.

Key:

```text
ratelimit:{policy_version}:{tenant_id}:{actor_id}:{route_id}
```

Recommended initial algorithm: Redis token bucket implemented atomically with Lua.

Pseudocode:

```text
INPUT: capacity, refill_rate, now, requested_tokens
LOAD bucket tokens + last_refill
REFILL = min(capacity, tokens + elapsed * refill_rate)
IF REFILL < requested_tokens:
    DENY
ELSE:
    subtract requested_tokens
    persist state + TTL
    ALLOW
RETURN allowed, remaining, reset_hint
```

Requirements:

- atomic across processes
- deterministic 429 response
- safe headers only
- no user-controlled Redis key fragments without normalization
- route-specific fail behavior if Redis unavailable

### Acceptance test

Environment:

- gateway A
- gateway B
- one Redis
- one synthetic identity
- one route

Policy: 100 requests/window.

Test:

1. send >100 concurrent requests distributed across A and B
2. total accepted across both <=100
3. remaining requests return 429
4. restart A
5. continue requests
6. prove budget remains shared
7. stop Redis
8. verify configured fail-closed behavior on sensitive route

Evidence JSON:

```json
{
  "gate": "R9_RATE_LIMIT_CLUSTER",
  "status": "PASS",
  "gateway_instances": 2,
  "policy_capacity": 100,
  "attempted": 140,
  "accepted": 100,
  "rejected": 40,
  "shared_budget": true,
  "restart_preserved_budget": true,
  "redis_failure_policy_verified": true
}
```

## 5.5 Authentication

Gateway validates:

- signature
- issuer
- audience
- expiry
- not-before
- tenant mapping

Never log:

- bearer token
- session cookie
- refresh token
- auth code

## 5.6 Authorization

Gateway performs coarse route authorization. Downstream service performs action-level validation.

## 5.7 Correlation ID

Rules:

- accept inbound correlation ID only if syntactically valid and policy allows
- otherwise generate UUID
- propagate to upstream
- include safe response header
- log in every event

## 5.8 Upstream allowlist and SSRF controls

Routing table contains configured service IDs, not arbitrary URLs from request input.

Disallowed:

- arbitrary host from query/body
- redirect to untrusted host with credential forwarding
- embedded URL credentials
- scheme outside allowed set

## 5.9 Retry policy

| Operation | Retry |
|---|---|
| GET/HEAD | bounded, only if route policy permits |
| POST without idempotency guarantee | no |
| POST with idempotency contract | bounded |
| auth decision | no loop |
| rate-limit decision | no loop |
| provider call | delegated to provider router policy |

## 5.10 Cache policy

Initially cache only:

- capability catalog
- public/static metadata
- short-TTL health summary if policy permits

Never cache:

- credential material
- approval results
- sensitive personalized responses
- side-effect response without explicit contract

## 5.11 BFF aggregation

For Web/Telegram/LINE-style clients:

```text
BFF Request
 → fan out to approved read services
 → bounded parallelism
 → collect results
 → normalize partial failure
 → emit one frontend response
```

No unbounded fan-out.

## 5.12 Gateway health

`/health/live`

- process event loop alive
- no dependency requirement

`/health/ready`

- route config valid
- auth verifier initialized
- Redis reachable if mandatory
- required policy metadata loaded
- critical internal endpoints resolvable by configured service registry

## 5.13 Gateway error contract

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Request limit exceeded.",
    "correlation_id": "uuid",
    "retryable": true
  }
}
```

No stack trace in public response.

## 5.14 Minimal OpenAPI seed

```yaml
openapi: 3.1.0
info:
  title: CK-NEXUS Gateway API
  version: 0.9.0
paths:
  /health/live:
    get:
      responses:
        '200': {description: Process is alive}
  /health/ready:
    get:
      responses:
        '200': {description: Gateway ready}
        '503': {description: Dependency/policy not ready}
  /api/v1/system/status:
    get:
      security: [{bearerAuth: []}]
      responses:
        '200': {description: Aggregated safe system status}
        '401': {description: Unauthorized}
        '429': {description: Rate limited}
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

## 5.15 R9 Definition of Done

- [ ] gateway package implemented
- [ ] auth unit/integration tests PASS
- [ ] downstream authorization envelope validated
- [ ] upstream allowlist and redirect safety tests PASS
- [ ] two-instance Redis rate limit test PASS
- [ ] restart preserves shared budget
- [ ] correlation ID E2E PASS
- [ ] audit event schema PASS
- [ ] sensitive route fail-closed PASS
- [ ] no secrets in public responses/logs
- [ ] R8 regression remains green
- [ ] exact commit and artifact fingerprint recorded

---

# L4 — Orchestration / R10

# 6. R10 Objective

Replace hard-coded workflow selection with a declarative, versioned, auditable Pattern Library. The Lead Orchestrator selects a pattern; the Development Council contributes specialist analysis; the Execution Controller alone owns side effects.

## 6.1 Roles

### Lead Orchestrator

- classify intent
- select pattern
- allocate agents
- resolve conflicts
- enforce time/step budget
- produce final plan

### Architect & Strategist

- architecture
- roadmap
- trade-offs
- dependency ordering

### Research & Analyst

- evidence
- comparisons
- source quality
- unknowns

### Product & UX Designer

- user flow
- product value
- interaction design
- adoption friction

### Engineering & Automation Builder

- implementation plan
- APIs
- queues
- integrations
- automation

### Security / QA / DevOps Reviewer

- threat review
- test plan
- deployment/recovery
- release gate review

### Execution Controller

- receives approved plan
- checks tool policy
- acquires idempotency key
- executes bounded side effect
- emits audit

## 6.2 Pattern lifecycle

```text
Intent
 → Pattern Match
 → Policy Load
 → Context Build
 → Plan
 → Tool Request
 → Guardrail Check
 → Execute Step
 → Verify
 → Approval
 → Deliver
 → Audit
 → Learning Feedback
```

## 6.3 Pattern schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CKNexusWorkflowPattern",
  "type": "object",
  "required": [
    "id", "version", "intent_tags", "agents",
    "allowed_tools", "forbidden_tools", "approval_policy",
    "side_effect_policy", "max_steps", "timeout_seconds"
  ],
  "properties": {
    "id": {"type": "string"},
    "version": {"type": "string"},
    "intent_tags": {"type": "array", "items": {"type": "string"}},
    "agents": {"type": "array", "items": {"type": "string"}},
    "allowed_tools": {"type": "array", "items": {"type": "string"}},
    "forbidden_tools": {"type": "array", "items": {"type": "string"}},
    "approval_policy": {"type": "string"},
    "side_effect_policy": {"type": "string"},
    "max_steps": {"type": "integer", "minimum": 1, "maximum": 100},
    "max_parallelism": {"type": "integer", "minimum": 1, "maximum": 20},
    "timeout_seconds": {"type": "integer", "minimum": 1},
    "retry_policy": {"type": "object"},
    "evidence_requirements": {"type": "array", "items": {"type": "string"}},
    "output_schema": {"type": "string"}
  }
}
```

## 6.4 Initial pattern registry

```yaml
patterns:
  - id: lead_research
    version: "1.0"
    intent_tags: [lead, prospect, research, sales]
    agents: [intake, research, enrichment, scoring, drafting, reviewer]
    allowed_tools: [web_search, crm_read, knowledge_search]
    forbidden_tools: [external_send, production_deploy]
    approval_policy: human_before_outbound
    side_effect_policy: draft_only
    max_steps: 12
    max_parallelism: 3
    timeout_seconds: 180

  - id: content_creation
    version: "1.0"
    intent_tags: [content, script, campaign, post]
    agents: [intake, research, draft, critic, reviewer]
    allowed_tools: [web_search, knowledge_search, content_store]
    forbidden_tools: [direct_publish]
    approval_policy: policy_before_publish
    side_effect_policy: queue_only
    max_steps: 14
    max_parallelism: 3
    timeout_seconds: 240

  - id: dataops_release_gate
    version: "1.0"
    intent_tags: [release, staging, build, test, deploy]
    agents: [planner, engineering, security_reviewer, reporter]
    allowed_tools: [compile, test, static_scan, staging_gate, evidence_writer]
    forbidden_tools: [unapproved_production_deploy]
    approval_policy: human_before_production
    side_effect_policy: staging_only
    max_steps: 30
    max_parallelism: 4
    timeout_seconds: 1800

  - id: credential_anomaly_monitor
    version: "1.0"
    intent_tags: [credential, anomaly, security, monitoring]
    agents: [security_reviewer, analyst, reporter]
    allowed_tools: [audit_read, metrics_read, alert_write]
    forbidden_tools: [credential_export, offensive_action]
    approval_policy: approval_for_quarantine
    side_effect_policy: alert_first
    max_steps: 10
    max_parallelism: 2
    timeout_seconds: 120

  - id: knowledge_synthesis
    version: "1.0"
    intent_tags: [summarize, compare, synthesize, knowledge]
    agents: [research, analyst, reviewer]
    allowed_tools: [knowledge_search, document_read, web_search]
    forbidden_tools: [external_send, deploy]
    approval_policy: none_for_read_only
    side_effect_policy: knowledge_write_only
    max_steps: 12
    max_parallelism: 4
    timeout_seconds: 180

  - id: product_idea_exploration
    version: "1.0"
    intent_tags: [idea, product, opportunity, strategy]
    agents: [architect, research, product, engineering, reviewer]
    allowed_tools: [idea_engine, knowledge_search, web_search]
    forbidden_tools: [publish, billing_mutation, deploy]
    approval_policy: human_before_execution
    side_effect_policy: proposal_only
    max_steps: 18
    max_parallelism: 5
    timeout_seconds: 300
```

## 6.5 Pattern selector output

```json
{
  "pattern_id": "dataops_release_gate",
  "version": "1.0",
  "confidence": 0.91,
  "reasons": ["release", "staging", "security gate"],
  "requires_human_approval": true,
  "fallback_pattern": null
}
```

## 6.6 Pattern selection rules

1. deterministic rules first for high-risk intents
2. model-assisted classification only within policy bounds
3. low confidence routes to manual/council review
4. pattern version locked for execution lifetime
5. audit stores selected pattern + reasons

## 6.7 Execution state machine

```text
CREATED
 → PLANNING
 → READY
 → RUNNING
 → VERIFYING
 → WAITING_APPROVAL (optional)
 → DELIVERING
 → COMPLETED

Failure branches:
RUNNING → RETRY_WAIT → RUNNING
RUNNING → BLOCKED
RUNNING → FAILED
VERIFYING → REPAIRING → VERIFYING
REPAIRING → ROLLBACK → FAILED/RECOVERED
```

## 6.8 Guardrail contract

Before every tool call:

```text
check actor
check pattern version
check allowed_tools
check forbidden_tools
check permission
check circuit breaker
check credential scope
check idempotency
check approval state
check timeout budget
```

Any failed check returns a structured deny/block result and audit event.

## 6.9 Approval record

```json
{
  "approval_id": "uuid",
  "execution_id": "uuid",
  "step_id": "step-12",
  "requested_by": "agent-or-service-id",
  "required_role": "owner|admin|reviewer",
  "decision": "pending|approved|rejected|expired",
  "decided_by": null,
  "reason": null,
  "expires_at": "RFC3339",
  "created_at": "RFC3339"
}
```

## 6.10 NEXUS-X CRANE alignment

Map the resilience concepts as follows:

- **Circuit** → provider/service circuit breaker
- **Canary** → bounded rollout of new workflow/provider/model policy
- **Repair** → approved remediation step executed in a controlled state machine
- **Rollback** → return to last known-safe config/artifact
- **Kill switch** → global or tenant-scoped execution disable

No agent may alter these controls without an authorized control-plane action.

## 6.11 Ω∞ alignment

Use Ω∞ as the conceptual continuous loop:

```text
Observe → Think → Plan → Act → Verify → Learn → Reframe → Observe
```

Implementation stays bounded by policy, budgets and human approval. “Infinite” denotes iterative learning, not unbounded execution.

## 6.12 R10 Definition of Done

- [ ] registry validates schema
- [ ] pattern selector deterministic tests PASS
- [ ] six initial patterns tested
- [ ] approval bypass tests fail safely
- [ ] forbidden-tool tests fail safely
- [ ] circuit-breaker integration PASS
- [ ] pattern/version/step stored in audit
- [ ] raw vault secrets never enter agent context
- [ ] Council remains advisory
- [ ] Execution Controller owns side effects

---

# L5 — Idea / Creativity Engine / R11

# 7. R11 Objective

Create a structured idea-expansion layer that turns vague inputs into connected, reviewable proposals without gaining direct execution authority.

## 7.1 Canonical idea pipeline

```text
Idea In
 → Clarify Blind Spots
 → Improve Understanding
 → Decision & Strategy
 → Creative Problem Solving
 → Self-Reflection
 → Data Insight
 → Hidden Opportunity
 → Structured Idea Packet
 → Knowledge Note Graph
 → L4 Pattern Selector
```

## 7.2 Stage definitions

### Stage 1 — Clarify

Capture:

- goal
- target user
- current problem
- constraints
- desired outcome
- urgency
- known facts
- unknowns

### Stage 2 — Understand

Separate:

- facts
- assumptions
- hypotheses
- missing evidence
- dependencies

### Stage 3 — Strategy

Generate options with:

- benefit
- cost
- risk
- time
- reversibility
- dependency burden

### Stage 4 — Create

Methods:

- combine existing ideas
- invert assumption
- simplify workflow
- automate repetitive middle steps
- productize reusable output
- shift actor from human labor to agent labor where safe

### Stage 5 — Reflect

Ask:

- what could fail?
- what conflicts with current architecture?
- what new attack surface appears?
- what creates operational burden?
- what should remain manual?

### Stage 6 — Data Insight

Define:

- metrics
- evidence needed
- benchmark
- experiment
- success threshold

### Stage 7 — Hidden Opportunity

Search adjacency:

- reuse
- bundling
- templates
- marketplace
- managed service
- internal efficiency
- new audience
- new integration
- new data product

### Stage 8 — Structure

Create proposal + graph nodes.

## 7.3 Lens registry

Initial lenses:

- SWOT
- Business Model Canvas
- Blue Ocean
- Design Thinking
- Jobs-to-be-Done
- Cost / Risk / Impact
- System Design
- Security & Governance
- Automation Opportunity
- Productization

## 7.4 Lens selection

Input features:

```json
{
  "idea_type": "product|process|marketing|architecture|security|business",
  "uncertainty": 0.7,
  "novelty": 0.8,
  "risk": 0.4,
  "evidence_availability": 0.5,
  "time_horizon": "short|medium|long"
}
```

Output picks only 1–3 lenses per pass to avoid framework overload.

## 7.5 Note graph model

Node types:

```text
idea
problem
assumption
evidence
decision
experiment
risk
opportunity
constraint
framework_output
metric
persona
workflow
integration
```

Edge types:

```text
supports
conflicts_with
depends_on
extends
derived_from
alternative_to
evidence_for
mitigates
enables
blocks
validates
invalidates
```

## 7.6 Idea node schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CKNexusIdeaNode",
  "type": "object",
  "required": ["id", "type", "title", "summary", "status", "created_at"],
  "properties": {
    "id": {"type": "string"},
    "type": {"enum": ["idea","problem","assumption","evidence","decision","experiment","risk","opportunity","constraint","framework_output","metric","persona","workflow","integration"]},
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "status": {"enum": ["draft","active","validated","rejected","archived"]},
    "tags": {"type": "array", "items": {"type": "string"}},
    "source_refs": {"type": "array", "items": {"type": "string"}},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "created_at": {"type": "string"},
    "updated_at": {"type": ["string","null"]}
  }
}
```

## 7.7 Edge model

```json
{
  "edge_id": "uuid",
  "from_node_id": "uuid",
  "to_node_id": "uuid",
  "type": "extends",
  "weight": 0.8,
  "reason": "Adds distributed rate limiting to existing gateway idea",
  "created_by": "service-or-user",
  "created_at": "RFC3339"
}
```

## 7.8 Dedup and novelty

Before creating a new node:

1. semantic retrieve similar nodes
2. compare type + tags + title
3. compute similarity score
4. if above threshold:
   - attach as `extends` / `alternative_to`, or
   - update proposal reference
5. preserve original node history
6. never silently overwrite

## 7.9 Opportunity scoring

Suggested score:

```text
OpportunityScore =
  0.25 * user_value
+ 0.20 * strategic_fit
+ 0.15 * reuse_potential
+ 0.15 * automation_gain
+ 0.10 * revenue_potential
+ 0.10 * evidence_strength
+ 0.05 * reversibility
- 0.20 * risk
- 0.15 * implementation_cost
```

Scores are guidance, not automated approval.

## 7.10 Proposal packet

```json
{
  "proposal_id": "uuid",
  "title": "Distributed API Gateway for CK-NEXUS",
  "summary": "...",
  "recommended_pattern": "dataops_release_gate",
  "benefits": [],
  "risks": [],
  "assumptions": [],
  "evidence_needed": [],
  "next_experiments": [],
  "related_node_ids": [],
  "opportunity_score": 0.74,
  "requires_human_approval": true
}
```

## 7.11 Idea Engine safety boundary

Idea Engine may:

- read approved knowledge
- write scoped knowledge metadata
- create proposals
- link nodes
- request research

Idea Engine may not:

- deploy
- publish externally
- send outbound communication
- mutate billing
- request/export raw credentials
- alter approval decisions
- modify release gates

## 7.12 Productization outputs

The Idea Engine should be able to identify reusable outputs such as:

- workflow templates
- prompt/policy packs
- integration recipes
- content automation packs
- knowledge-base packs
- reporting templates
- vertical industry bundles
- consulting setup playbooks

## 7.13 R11 Definition of Done

- [ ] graph schema validates
- [ ] node/edge CRUD preserves audit history
- [ ] similarity/dedup tests PASS
- [ ] lens selector tests PASS
- [ ] opportunity scoring deterministic tests PASS
- [ ] proposal packet validates
- [ ] proposal integrates with R10 selector
- [ ] no-side-effect negative tests PASS
- [ ] graph export excludes secrets

---

# 8. Cross-Cutting Security and Governance

## 8.1 Identity & Access

- RBAC/ABAC where appropriate
- least privilege
- tenant isolation
- MFA/SSO compatibility
- service identity rotation

## 8.2 Credential behavior monitoring

Detect:

- unusual lease frequency
- new consumer for sensitive secret
- repeated denied purpose
- abnormal scope
- access outside normal time/tenant pattern

Response order:

```text
Detect → Alert → Review → Restrict/Quarantine if policy permits → Rotate/Revoke → Audit
```

## 8.3 Security event categories

- auth failure
- permission denial
- credential denial
- policy violation
- rate-limit anomaly
- unexpected upstream redirect
- circuit breaker open
- repeated provider error
- approval bypass attempt
- integrity mismatch

## 8.4 Defensive threat model

Protect against:

- credential leakage
- SSRF through dynamic upstreams
- privilege escalation
- replay and duplicate side effects
- tenant boundary failure
- poisoned workflow config
- unsafe retry loops
- dependency cascade failure
- audit tampering
- silent production drift

## 8.5 Policy hierarchy

```text
Global safety policy
  → environment policy
  → tenant policy
  → route/workflow policy
  → tool policy
  → execution step policy
```

Lower layers may restrict further but may not override a stricter higher-level deny.

---

# 9. Observability Standard

## 9.1 Required signals

### Metrics

- request count / latency / error
- rate-limit allow/deny
- circuit state
- provider success/failure
- queue depth / age
- workflow duration
- approval wait time
- credential lease count/deny
- database pool usage
- Redis health
- backup age

### Logs

Structured JSON; never secret-bearing.

### Traces

At minimum logical spans:

```text
gateway.request
orchestrator.select_pattern
orchestrator.plan
workflow.step
provider.execute
approval.wait
delivery.execute
audit.write
```

## 9.2 SLO seed

Initial, to be calibrated from staging:

- health/live: 99.9% process availability target
- health/ready: reflects dependency readiness honestly
- interactive API p95 latency tracked per route class
- workflow success rate tracked per pattern
- duplicate external side-effect target: zero
- unredacted secret exposure target: zero

Do not turn these into contractual SLA until measured in staging/production.

---

# 10. Frontend / UX Operating Discipline

## 10.1 UI architecture

Recommended areas:

```text
Control Hub
Development Council
Workflow Runs
Integrations
Knowledge / Idea Graph
Approvals
Observability
Release Gates
Settings / Security
```

## 10.2 State model

UI distinguishes:

- loading
- ready
- partial
- blocked
- failed
- degraded
- disconnected
- approval required

Do not collapse `BLOCKED` into `FAILED`.

## 10.3 React rules

- typed API client
- cancel inflight requests on unmount/navigation
- cleanup subscriptions/listeners
- no hidden mutable global state without owner
- no secret storage in localStorage
- sensitive server actions require server-side authorization

## 10.4 UX flow for autonomous actions

```text
User intent
 → system proposal
 → scope/impact preview
 → approval if required
 → execution progress
 → verification result
 → evidence/audit link
 → next recommendation
```

---

# 11. Development and Git Discipline

## 11.1 Branching

One release slice per branch:

```text
r9-api-gateway
r10-pattern-library
r11-idea-engine
r12-staging-evidence
```

## 11.2 Commit discipline

- small meaningful commits
- no unrelated generated noise
- no secrets
- tests with feature
- migration with schema change
- doc/contract update with public behavior change

## 11.3 Merge discipline

Before merge:

- pull/rebase current base according to repo policy
- compile
- unit tests
- integration tests
- static analysis
- secret scan
- diff check
- contract/schema validation
- migration review

## 11.4 Five mandatory system-design questions

Every new service or major endpoint must document:

1. caching policy
2. rate limiting
3. idempotency
4. sync vs queue decision
5. CAP/consistency trade-off

Additional mandatory questions:

6. timeout and retry budget
7. observability signals
8. failure/degradation behavior
9. secret/identity requirements
10. rollback strategy

---

# 12. R12 — Staging Evidence Sprint

# 12.1 Objective

Close inherited production blockers using actual production-like staging evidence. Unit tests, mocks, local SQLite results or documentation are not substitutes.

## 12.2 Evidence identity

Every gate artifact contains:

```json
{
  "run_id": "uuid",
  "gate_id": "EMAIL001",
  "status": "PASS|FAIL|BLOCKED",
  "commit_sha": "40-char-sha",
  "artifact_sha256": "sha256",
  "environment_id": "staging-unique-id",
  "started_at": "RFC3339",
  "finished_at": "RFC3339",
  "evidence_refs": [],
  "summary": {},
  "errors": []
}
```

## 12.3 Evidence rules

- evidence lives outside repo or immutable mount
- every gate emits valid JSON
- missing gate is never PASS
- missing worker/harness is BLOCKED
- final gate loads explicit required-gate registry
- each required gate appears exactly once
- all identity fields match the same release artifact and staging environment

## 12.4 Required gates

### EMAIL001 — PostgreSQL 100-way hard dedup

Requirements:

- production-like PostgreSQL schema
- 100 concurrent attempts with same synthetic key
- exactly 1 winner
- 99 duplicate/rejected outcomes
- exactly one outbox/external side-effect record

Evidence must be machine-readable.

### EMAIL002 — Provider timeout / retry / outbox

- deterministic provider failure injection
- unique provider request IDs
- bounded retry
- zero duplicate external effect

### EMAIL003 — SIGKILL / lease expiry / reclaim

- worker acquires lease
- worker is killed
- lease expires/reclaims
- another worker completes exactly once
- missing worker harness = BLOCKED

### EMAIL004 — Deterministic n8n routing

- actual staging n8n workflow
- fixed input corpus
- expected route/action asserted

### EMAIL005 — Attachment quarantine

- exercise actual email pipeline
- use synthetic suspicious fixture
- prove quarantine
- prove audit event

### EMAIL006 — Loop prevention

- synthetic self-trigger / echo case
- prove loop detector halts repeated processing

### EMAIL007 — Correlation ID E2E

Trace one correlation ID through:

```text
Gateway → Email/Service → Workflow/Provider → Audit
```

### BACKUP001 — Destructive backup/restore/boot/health/smoke

Safety preconditions:

```text
ENVIRONMENT=staging
ALLOW_DESTRUCTIVE_P0_DRILL=YES
COMPOSE_PROJECT_NAME=<unique-staging-project>
SAFETY_SENTINEL=<expected-value>
```

Procedure:

1. verify staging marker
2. create backup
3. destroy isolated staging data/volume
4. restore
5. boot
6. health
7. smoke
8. compare expected data markers

Never run destructive drill against ambiguous environment.

### AI001 — Live OpenAI production-path smoke

- credential is already present in secret manager/environment
- never echo/export inline
- call through CK-NEXUS Provider Router / runtime
- record sanitized provider/model/latency/correlation metadata
- no response-content grep as evidence

### SEC001 — Security tooling + n8n audit

- real secret scan
- Bandit/static scan
- dependency audit
- real `n8n audit`
- raw outputs archived
- policy defines unacceptable findings

### OBS001 — Observability + actual alert delivery

- health/metrics/log correlation
- inject controlled failure
- prove alert is delivered to configured sink

### OPS001 — Clean-machine deployment

- fresh staging host/VM
- exact artifact
- no hidden local state
- install
- migrate
- boot
- readiness
- smoke

## 12.5 Required gate registry

```yaml
required_gates:
  - EMAIL001
  - EMAIL002
  - EMAIL003
  - EMAIL004
  - EMAIL005
  - EMAIL006
  - EMAIL007
  - BACKUP001
  - AI001
  - SEC001
  - OBS001
  - OPS001
```

## 12.6 Final decision algorithm

```python
def final_release_decision(required_gates, evidence):
    indexed = index_by_gate_id(evidence)

    for gate in required_gates:
        matches = indexed.get(gate, [])
        if len(matches) != 1:
            return "NO-GO"
        if matches[0]["status"] != "PASS":
            return "NO-GO"

    identities = {
        (e["commit_sha"], e["artifact_sha256"], e["environment_id"])
        for e in evidence
        if e["gate_id"] in required_gates
    }
    if len(identities) != 1:
        return "NO-GO"

    return "PRODUCTION-READY-CANDIDATE"
```

This result is a technical production candidate only; legal, commercial, support and operational approvals remain separate.

---

# 13. Release Roadmap R9–R12

## R9 — API Gateway

### Purpose

Close the distributed rate-limit gap and establish one controlled external edge.

### Dependencies

- R8 vault baseline
- Redis staging
- existing auth identity model or minimal gateway verifier

### Exit

- two-instance rate limit evidence
- auth/routing/audit PASS
- correlation PASS
- SSRF/upstream controls PASS
- fail-closed PASS

## R10 — Pattern Library

### Purpose

Make existing agents reusable through declarative workflow patterns.

### Dependencies

- R9 identity/correlation envelope
- R6 circuit breaker
- R5 Development Council

### Exit

- registry validation
- pattern selection
- guardrail enforcement
- approval independence
- audit trace

## R11 — Idea Engine

### Purpose

Create compounding creative knowledge without adding dangerous execution authority.

### Dependencies

- R10 proposal/pattern interface
- knowledge store

### Exit

- note graph
- lens selector
- dedup
- opportunity scoring
- proposal integration

## R12 — Evidence Sprint

### Purpose

Close every technical production blocker.

### Dependencies

- exact release artifact candidate
- staging environment
- real PostgreSQL, Redis, n8n, alert sink, provider credentials, backup target

### Exit

Every required gate exists exactly once and is PASS with matching release identity.

---

# 14. Suggested Implementation Order Inside Each Release

## R9 implementation order

```text
1. gateway config + health
2. correlation middleware
3. auth verifier
4. route registry / allowlist
5. Redis rate limiter
6. proxy/upstream client
7. audit middleware
8. BFF read aggregation
9. integration tests
10. multi-instance staging test
```

## R10 implementation order

```text
1. pattern JSON schema
2. registry loader
3. selector
4. execution context
5. guardrail evaluator
6. approval model
7. audit integration
8. initial patterns
9. Council integration
10. negative tests
```

## R11 implementation order

```text
1. idea node / edge schema
2. graph repository
3. similarity retrieval
4. dedup linker
5. lens registry
6. idea pipeline
7. opportunity score
8. proposal packet
9. R10 integration
10. no-side-effect tests
```

## R12 implementation order

```text
1. evidence JSON schema
2. gate registry
3. isolated evidence directory
4. PostgreSQL dedup harness
5. provider fault harness
6. worker kill/reclaim harness
7. n8n route + audit
8. backup/restore drill
9. live OpenAI smoke
10. alert delivery test
11. clean-machine deploy
12. final decision compiler
```

---

# 15. Target Runtime Request Lifecycle

```text
Client
  │
  ▼
L3 Gateway
  ├─ Correlation
  ├─ Auth
  ├─ Rate Limit
  ├─ Route Policy
  │
  ▼
L4 Orchestrator
  ├─ Intent
  ├─ Pattern
  ├─ Council / Planner
  ├─ Guardrails
  │
  ▼
L2 Core Services
  ├─ Credential Broker
  ├─ Provider Router
  ├─ Email / Billing / Integrations
  │
  ▼
L1 Data & Infra
  ├─ Postgres
  ├─ Redis
  ├─ Queue
  ├─ Vault
  │
  ▼
Verification / Approval
  │
  ▼
Delivery + Audit
  │
  ▼
L5 Idea / Learning
  └─ knowledge links / proposals / improvements
```

---

# 16. Failure and Degradation Matrix

| Failure | Expected behavior |
|---|---|
| Redis rate-limit unavailable | sensitive routes fail-closed; explicitly allowed read routes may degrade per policy |
| OpenAI circuit open | route to approved fallback if policy permits; otherwise blocked, never endless retry |
| Ollama unavailable | fallback only if allowed; readiness reflects configured criticality |
| Vault unavailable | operations requiring credentials BLOCKED |
| PostgreSQL unavailable | readiness false for durable mutation paths |
| n8n unavailable | n8n-dependent workflows BLOCKED/DEGRADED; unrelated services remain available |
| Audit store unavailable | sensitive side effects default fail-closed if audit is mandatory |
| Approval service unavailable | approval-required action remains pending/blocked |
| Alert sink unavailable | OBS gate fails; do not claim alerting works |
| Idea Engine unavailable | core execution continues; creativity features degrade only |

---

# 17. Data Ownership Matrix

| Domain | System of record | Cache/coordination |
|---|---|---|
| users/tenants | PostgreSQL | optional Redis cache |
| workflow execution | PostgreSQL | Redis lease/lock |
| rate limits | Redis | none |
| credential encrypted material | Vault store | broker lease metadata |
| audit | PostgreSQL/append-only store | optional stream |
| idea graph | PostgreSQL + vector metadata | retrieval cache |
| provider circuit state | shared coordination or durable state as designed | Redis acceptable |
| approvals | PostgreSQL | notification cache only |
| outbox | PostgreSQL | worker queue |

---

# 18. API Surface Target

External gateway examples:

```text
GET  /health/live
GET  /health/ready
GET  /api/v1/system/status
GET  /api/v1/integrations/status
POST /api/v1/council/consult
POST /api/v1/workflows/run
GET  /api/v1/workflows/{execution_id}
POST /api/v1/approvals/{approval_id}/decision
POST /api/v1/ideas/expand
GET  /api/v1/ideas/{id}
GET  /api/v1/knowledge/search
```

Internal-only examples:

```text
POST /internal/credentials/lease
POST /internal/providers/execute
POST /internal/audit/events
POST /internal/workflows/step
POST /internal/ideas/link
```

Internal endpoints are not exposed directly to public clients.

---

# 19. Canonical Execution Context

```json
{
  "tenant_id": "tenant-1",
  "actor": {
    "id": "user-1",
    "type": "human",
    "roles": ["owner"],
    "permissions": ["workflow.run", "idea.expand"]
  },
  "correlation_id": "uuid",
  "request_id": "uuid",
  "execution_id": "uuid",
  "environment": "staging",
  "policy_version": "2026-08-09.1",
  "pattern": {
    "id": "product_idea_exploration",
    "version": "1.0"
  },
  "budgets": {
    "max_steps": 18,
    "max_parallelism": 5,
    "timeout_seconds": 300
  },
  "approval": {
    "required": true,
    "state": "pending"
  }
}
```

---

# 20. Configuration Principles

## 20.1 Environment

Use configuration for non-secret behavior; secret manager/vault for secrets.

Example non-secret configuration:

```env
CKN_ENV=staging
CKN_GATEWAY_FAIL_CLOSED=true
CKN_RATE_LIMIT_BACKEND=redis
CKN_PROVIDER_POLICY=mock,ollama,openai
CKN_OLLAMA_ALLOW_LOOPBACK_ONLY=true
CKN_AUDIT_REQUIRED=true
CKN_APPROVAL_REQUIRED_FOR_PRODUCTION=true
```

Secret examples are referenced by secret IDs, not values.

## 20.2 Policy versioning

Every policy file receives a version/hash and is included in audit events.

---

# 21. Testing Pyramid

## Unit

- pure policy logic
- schema validation
- routing decisions
- rate-limit algorithm wrapper
- idea scoring

## Integration

- gateway + Redis
- gateway + auth verifier
- orchestrator + pattern registry
- broker + vault
- provider router + mocked provider transport
- workflow + PostgreSQL

## Staging

- real PostgreSQL concurrency
- real Redis multi-process rate limit
- real n8n route/audit
- live OpenAI path
- backup/restore
- alert delivery
- clean-machine deploy

## Negative tests

Must include:

- malformed JWT
- expired JWT
- cross-tenant attempt
- forbidden tool
- approval bypass
- duplicate idempotency key
- unsafe redirect
- vault unavailable
- rate-limit Redis unavailable
- circuit open
- missing required gate

---

# 22. Product / Business Expansion Map

The architecture supports productization without changing core security boundaries.

## 22.1 Content & Research Automation

- research synthesis
- script/content generation
- competitor monitoring
- reusable content workflows

## 22.2 Sales & Lead Operations

- lead enrichment
- scoring
- message drafting
- approval-before-send

## 22.3 Customer Support

- triage
- knowledge answer
- escalation
- satisfaction analysis

## 22.4 Knowledge Management

- document ingestion
- RAG
- linked notes
- FAQ generation
- decision history

## 22.5 Internal Operations

- email routing
- reporting
- analytics
- release evidence
- alerts

## 22.6 Productized AI Services

- workflow packs
- templates
- managed knowledge systems
- premium integrations
- setup/consulting
- training/workshops

---

# 23. Automation Maturity Model

## Level 1 — Assist

AI suggests; human acts.

## Level 2 — Guided

AI selects from approved templates; human approves key decisions.

## Level 3 — Automated

Bounded workflows execute automatically with logs and limits.

## Level 4 — Governed

Automation is policy-driven, audited, approval-aware and recoverable.

## Level 5 — Self-Improving

System learns from outcomes and proposes improvements, but changes to production behavior still pass governance gates.

CK-NEXUS R9–R12 target is **Level 4 with controlled Level-5 learning proposals**, not unrestricted self-modification.

---

# 24. Repository Shape After Future Split

This single document can later split into:

```text
ck-nexus/
  gateway/
  creator_app/
  orchestration/
  idea_engine/
  integrations/
  security/
  observability/
  evidence/
  schemas/
  contracts/
  config/
  scripts/
  tests/
  docs/
```

Suggested mapping:

```text
Sections 4–5  → docs/architecture + gateway/
Section 6     → orchestration/
Section 7     → idea_engine/
Section 8     → security/
Section 9     → observability/
Section 12    → evidence/ + scripts/p0/
Schemas       → schemas/
OpenAPI       → contracts/
Policies      → config/
```

---

# 25. Release Gate Checklist — Master

## R9

- [ ] Gateway public edge exists
- [ ] Auth verified
- [ ] Downstream authz verified
- [ ] Shared Redis rate limiting proven across 2+ processes
- [ ] Route allowlist
- [ ] SSRF/redirect credential protections
- [ ] Correlation E2E
- [ ] Audit
- [ ] Fail-closed

## R10

- [ ] Pattern registry
- [ ] Pattern selector
- [ ] Council mapping
- [ ] Tool allowlist
- [ ] Forbidden tool deny
- [ ] Approval independence
- [ ] Circuit integration
- [ ] Pattern/version audit

## R11

- [ ] Idea pipeline
- [ ] Note graph
- [ ] Dedup
- [ ] Lens selector
- [ ] Opportunity scoring
- [ ] Proposal packet
- [ ] R10 integration
- [ ] No side effects

## R12

- [ ] EMAIL001
- [ ] EMAIL002
- [ ] EMAIL003
- [ ] EMAIL004
- [ ] EMAIL005
- [ ] EMAIL006
- [ ] EMAIL007
- [ ] BACKUP001
- [ ] AI001
- [ ] SEC001
- [ ] OBS001
- [ ] OPS001
- [ ] final identity consistency

---

# 26. Non-Goals Until After R12

Do not allow feature pressure to displace production evidence.

Until R12 closes:

- no claim of Production Ready
- no unrestricted autonomous deploy
- no arbitrary agent-created credentials
- no public multi-tenant scale claim without distributed gateway evidence
- no self-modifying production policy
- no silent auto-publish for high-impact external actions

---

# 27. Post-R12 Optional Direction

Only after technical production evidence is complete should the project consider new release families such as:

## R13 — Multi-Tenant SaaS Hardening

- tenant quotas
- tenant billing isolation
- per-tenant encryption policy
- admin delegation

## R14 — Marketplace / Template Runtime

- signed templates
- versioned workflow packs
- safe import/export

## R15 — Advanced Knowledge Graph

- graph analytics
- temporal decisions
- richer retrieval

## R16 — Policy Learning Assistant

- recommend policy changes
- simulation before activation
- human approval mandatory

These are proposals, not current commitments.

---

# 28. Definition of “Autonomous” in CK-NEXUS

Autonomous does **not** mean uncontrolled.

CK-NEXUS autonomous behavior means:

- the system can select an approved workflow
- allocate approved agents
- execute approved tools
- retry within bounded policy
- detect failure
- degrade safely
- request approval
- verify outcome
- learn and propose improvements

It does not mean:

- bypassing owner policy
- creating permissions for itself
- exporting secrets
- silently deploying high-risk changes
- ignoring release gates

---

# 29. Master Architectural Principles

1. **Context before action** — retrieve enough context before execution.
2. **Policy before autonomy** — no action outside declared policy.
3. **Evidence before production claims** — staging proof outranks local confidence.
4. **Fail closed for sensitive operations** — ambiguity should not become privilege.
5. **Agents advise, controllers execute** — preserve separation of duties.
6. **One correlation trail** — every important action is traceable.
7. **Idempotency by design** — retries must not multiply side effects.
8. **Secrets stay server-side** — models/status/UI receive metadata, not secret values.
9. **Composable layers** — each layer has a contract and can evolve independently.
10. **Learning proposes; governance disposes** — improvement loops create proposals, not uncontrolled production mutation.
11. **Human judgment remains explicit** — high-impact decisions preserve human authority.
12. **Build for rollback** — every significant change needs a recovery path.

---

# 30. Canonical “One Page” Summary

```text
CK-NEXUS
│
├── L3 GATEWAY
│   ├── identity
│   ├── distributed rate limiting
│   ├── safe routing
│   └── correlation/audit
│
├── L4 ORCHESTRATION
│   ├── Lead Orchestrator
│   ├── Development Council
│   ├── Pattern Library
│   ├── Guardrails
│   └── Approval / Execution Controller
│
├── L2 CORE SERVICES
│   ├── Credential Broker + Encrypted Vault
│   ├── Provider Router
│   ├── Gmail / GitHub App / integrations
│   ├── Email
│   ├── Billing
│   └── Audit
│
├── L1 DATA / INFRA
│   ├── PostgreSQL
│   ├── Redis
│   ├── Queue
│   ├── Backup/Restore
│   └── Evidence Store
│
└── L5 IDEA ENGINE
    ├── Clarify / Understand / Strategy
    ├── Create / Reflect / Data Insight
    ├── Hidden Opportunity
    ├── Lens Library
    └── Knowledge Note Graph

R9  = distributed gateway control
R10 = reusable governed agent workflows
R11 = structured creativity + graph memory
R12 = production staging evidence

Final rule:
NO production claim until all required R12 gates PASS
against one exact commit + artifact + environment identity.
```

---

# 31. Final Build Directive

The implementation should proceed from the verified R8 baseline in this order:

```text
R8 verified baseline
  ↓
R9 API Gateway
  ↓
R9 cluster-wide rate-limit proof
  ↓
R10 Pattern Library
  ↓
R10 Council/Execution separation proof
  ↓
R11 Idea Engine
  ↓
R11 no-side-effect + graph proof
  ↓
Freeze release candidate artifact
  ↓
R12 Staging Evidence Sprint
  ↓
All required gates PASS?
  ├─ NO  → RC / NO-GO, fix evidence or implementation
  └─ YES → Production-Ready Candidate for final operational/business review
```

This ordering is deliberate: **do not add additional architecture layers between R11 and R12 unless they are required to close a gate.** The project already has sufficient capability breadth; the highest-value transition is from “capable development candidate” to “evidenced, governable production candidate.”

---

# 32. Document Authority and Change Rule

This file is the canonical source until intentionally split.

Any future split must preserve:

- section IDs or equivalent traceability
- release lineage
- global invariants
- gate IDs
- security boundaries
- exact distinction between PASS / FAIL / BLOCKED
- R12 production rule

When split into code/spec/docs, generated files should contain a `source_section` or `source_revision` reference back to this master.

Recommended metadata for derived artifacts:

```yaml
source_document: CK-NEXUS-CANONICAL-MASTER-SOURCE-R9-R12.md
source_revision: 1
baseline_commit: ded79e08b930b5a6b733bcc658bfc9615d1b09a8
release_posture: RC_NO_GO
```

---

# END OF CANONICAL MASTER SOURCE
