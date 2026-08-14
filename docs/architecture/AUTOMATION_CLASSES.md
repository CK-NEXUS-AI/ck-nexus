# CK-NEXUS Automation Classes

Status: SPEC_ONLY
Version: 0.1

Each automation class runs the same guarded control loop:

`Observe -> Detect -> Classify -> Plan -> Policy/Risk -> Execute -> Verify -> Evidence -> Learn`

Learning may tune ranking and recommendations but MUST NOT override hard policy, approval, tenant, or kill-switch constraints.

## DiscoveryAutomation

Purpose: discover providers, connectors, tools, schemas, endpoints, installed plugins, and capability changes.

May perform read-only discovery and health probes. Any new candidate enters registry as untrusted/candidate until validated.

## IntegrationAutomation

Purpose: connect approved systems through Connection Fabric.

Responsibilities:
- auth scheme negotiation
- least-privilege scope proposal
- capability probing
- connector health
- contract compatibility
- topology updates
- credential lease refresh using official owner-authorized mechanisms

OAuth consent or new secret creation remains owner-controlled.

## DevelopmentAutomation

Purpose: build or adapt missing candidate capabilities in isolated workspaces.

Responsibilities:
- code generation/refactoring proposals
- test generation
- adapter scaffolding
- contract implementation
- candidate packaging

No direct production promotion.

## SecurityAutomation

Purpose: continuously evaluate security posture.

Responsibilities:
- policy conformance
- secret scanning
- dependency/supply-chain analysis
- static/dynamic security checks where authorized
- finding triage
- regression verification
- attack-path analysis when the designated tooling is available

It must distinguish supplemental security evidence from release-gate evidence.

## DataAutomation

Purpose: maintain durable data systems safely.

Responsibilities:
- migrations planning
- schema drift detection
- backup verification
- retention enforcement
- index maintenance
- reconciliation
- data quality checks

Destructive restore or production migration follows explicit change control.

## KnowledgeAutomation

Purpose: acquire, normalize, deduplicate, classify, and index approved knowledge.

Responsibilities:
- provenance capture
- freshness tracking
- semantic deduplication
- conflict detection
- graph linking
- retrieval evaluation

Knowledge ingestion is not model-weight modification and does not grant execution authority.

## ReleaseAutomation

Purpose: package exact source subjects and coordinate gates.

Responsibilities:
- evidence freshness checks
- provenance binding
- reproducible manifests
- release-note generation
- staged gate progression
- rollback package validation

Never marks GO when a required prior gate is blocked.

## RecoveryAutomation

Purpose: detect failures and perform bounded recovery.

Responsibilities:
- restart/retry
- checkpoint resume
- compensation
- failover
- canary rollback
- restore drill orchestration in isolated staging

Must classify uncertain side effects before retrying.

## CostAutomation

Purpose: optimize spend without evading provider policy.

Responsibilities:
- budget enforcement
- cost estimation
- free-tier preference
- local-provider preference where policy permits
- quota-aware routing
- anomaly detection

Forbidden behaviors include account/key farming, quota evasion, or hidden paid fallback when `free_only=true`.

## MonitoringAutomation

Purpose: convert metrics/events/logs/traces into actionable operational signals.

Responsibilities:
- SLO evaluation
- anomaly detection
- alert routing
- correlation across executions
- health scoring
- operator receipt verification for release drills

Observability signals guide control decisions but do not replace authoritative workflow/evidence state.

## PolicyAutomation

Purpose: evaluate declarative policy changes and policy drift.

Responsibilities:
- policy bundle validation
- impact simulation
- regression tests
- conflict detection
- policy provenance

PolicyAutomation cannot approve its own high-impact policy change.

## ReconciliationAutomation

Purpose: compare desired state, recorded state, and observed external state.

Typical cycle:
`desired -> recorded -> observed -> diff -> classify -> safe repair or escalation`.

This is critical for webhook loss, partial failure, and externally modified resources.

## CapabilityLifecycleAutomation

Purpose: manage capability status over time.

Responsibilities:
- candidate scoring
- health decay
- deprecation
- canary analysis
- quarantine/revocation
- compatibility tracking

It may recommend promotion, but release governance owns final trust transitions.

## Common execution contract

Every automation should expose:
- automation ID/version
- trigger contract
- input/output schemas
- maximum risk it may autonomously handle
- required approval classes
- retry/compensation policy
- evidence requirements
- checkpoint semantics
- kill-switch namespace
- tenant boundary
- cost budget semantics

This makes automations discoverable capabilities rather than hidden cron scripts.