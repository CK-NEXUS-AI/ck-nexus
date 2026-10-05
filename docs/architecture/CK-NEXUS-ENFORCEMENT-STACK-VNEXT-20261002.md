# CK-NEXUS Enforcement Stack vNext — P0 Upgrade

Date: 2026-10-02
Base: closure/one-shot-evidence-closure-20261002 @ 546797016270865cff47eccafdb30f04158ab088
Status: DESIGNED / NOT IMPLEMENTED / NOT VERIFIED

## Purpose

Upgrade CK-NEXUS from a governance-heavy control plane into a governed autonomous-system control plane with an explicit enforcement boundary.

This document is an architecture contract, not evidence of implementation.

## Non-negotiable invariants

1. MODEL/AGENT != AUTHORITY.
2. Policy must be enforceable outside model reasoning.
3. EXECUTED != VERIFIED.
4. APPROVED != EXECUTED.
5. Evidence must bind the exact policy, authority, artifact, action and result.
6. No credential is directly exposed to an agent when a brokered path is possible.
7. Fail closed on unknown or unmediated mutation paths.
8. Every production claim requires reproducible evidence.
9. A policy change must have impact analysis before activation.
10. A watchdog must be able to quarantine an agent without depending on the agent's cooperation.

## Target planes

### 1. Governance Control Plane

- Intent
- Agent Identity
- Lease
- Policy
- Approval
- Trust
- Admission
- Evidence
- Memory
- Recovery
- Compliance

### 2. Enforcement Plane

- Policy Decision Point
- Tool Firewall
- Network/API Firewall
- Credential Broker
- Process/Filesystem Sandbox
- Runtime capability enforcement
- Rate/budget/time limits

### 3. Watchdog Plane

- Independent health monitor
- Policy-violation monitor
- anomaly/risk monitor
- scoped quarantine
- scoped kill
- fleet kill
- recovery trigger

The watchdog must not share the same authority boundary as the agent being monitored.

## Policy decision contract

Every governed side effect should produce a deterministic decision record:

- decision_id
- subject/agent_id
- lease_id
- policy_version
- policy_hash
- action
- resource
- scope
- context_hash
- verdict: ALLOW | WARN | DENY | ESCALATE | TRANSFORM
- expiry
- decision_timestamp
- signer

The decision engine should be stateless and deterministic for the same canonical input snapshot and policy revision.

## Mandatory intervention points

CK-NEXUS vNext must support explicit enforcement hooks at:

- input
- pre-model
- post-model
- pre-tool
- post-tool
- network request
- credential request
- process spawn
- filesystem mutation
- output
- shutdown

An integration that bypasses these points is UNKNOWN/UNMEDIATED and must not receive production authority.

## Credential boundary

Agent-facing credentials are references, not raw secrets.

Required flow:

Agent -> Credential Broker -> identity/lease/policy/endpoint/method/resource checks -> short-lived scoped credential -> external service

The broker must record a redacted receipt without storing or emitting the secret.

## Policy lifecycle

Policy vN
-> canonical diff
-> impact analysis
-> proof/check
-> approval
-> signed activation
-> canary
-> observe
-> activate or rollback

Impact analysis must explicitly identify newly added authority, removed authority, changed resources, changed network destinations, credential scope changes and changed mutation capabilities.

## Cryptographic execution receipts

For every governed mutation:

Pre-action receipt:
- intent_hash
- policy_hash
- authority_hash
- approval_hash
- artifact_hash
- action_hash

Post-action receipt:
- pre_action_receipt_hash
- result_hash
- verification_hash
- evidence_hash
- signer
- timestamp

Receipts form a hash-linked chain and must be independently verifiable without trusting application logs alone.

## Governance coverage scanner

The system must enumerate:

- MEDIATED paths
- UNMEDIATED paths
- UNKNOWN paths

Examples requiring explicit detection:

- subprocess/child process
- direct socket/network access
- raw filesystem access
- unmanaged MCP server
- unmanaged browser session
- direct provider/API access
- agent-to-agent delegation
- background jobs
- scheduled jobs

No production admission while an authority-bearing mutation path is UNKNOWN.

## Agent admission

Agent/skill/MCP admission pipeline:

DISCOVERED
-> IDENTITY_VERIFIED
-> PROVENANCE_VERIFIED
-> LICENSE_REVIEWED
-> SECURITY_REVIEWED
-> SANDBOX_EXECUTED
-> BEHAVIOR_TESTED
-> TRUST_ASSESSED
-> ADMITTED
-> LEASED
-> CONTINUOUSLY_MONITORED
-> RE-ADMISSION

Admission certificates must bind artifact hash, version, capabilities, security evidence, policy compatibility, issuer and expiry.

## Agent-to-agent authority

Delegation must be attenuating:

parent authority >= child authority

A child must never gain a capability absent from the parent's active authority unless a separate human-authorized grant exists.

Every delegation receives:

- delegator
- delegatee
- parent lease
- delegated scope
- attenuation proof
- expiry
- delegation receipt

## Durable execution / SRE

Autonomous runs need:

- checkpoint
- lease
- retry policy
- idempotency key
- timeout
- budget
- circuit breaker
- cooldown
- quarantine
- rollback
- recovery event

Recovery must never silently convert a failed verification into success.

## Memory security

Memory writes must carry:

- source
- provenance
- tenant
- agent
- policy scope
- timestamp
- TTL
- integrity hash
- trust classification

Untrusted tool/model output must not become trusted memory without an explicit admission decision.

## Data and decision lineage

For every consequential action, preserve the relationship:

Input -> Context -> Memory -> Retrieval -> Model -> Policy -> Approval -> Tool -> Result -> Verification -> Action

The system must be able to answer both:

- What data influenced this action?
- Why was this action permitted?

## Multi-tenant boundary

Tenant isolation must cover:

- identity
- leases
- policies
- credentials
- agents
- memory
- evidence
- budgets
- runtime sandboxes

Cross-tenant reads/writes must be denied by default and independently tested.

## P0 implementation order

P0.1 Enforcement Gateway + Policy Decision contract
P0.2 Governance Coverage Scanner
P0.3 Credential Broker enforcement
P0.4 Policy impact analysis / prover interface
P0.5 Independent Watchdog + quarantine
P0.6 Cryptographic pre/post receipts
P0.7 Agent/MCP/Skill admission certificate
P0.8 Delegated authority
P0.9 Durable execution/SRE controls
P0.10 Memory/data/decision lineage

## Verification gates

Each component must move through:

DESIGNED
-> IMPLEMENTED
-> EXECUTED
-> VERIFIED
-> PRODUCTION

A design document, unit test, hash match, or local pass alone is not sufficient for VERIFIED.

## Current blockers inherited from the closure baseline

- Q10 NOT_VERIFIED
- Q11 BLOCKED
- Q12 BLOCKED
- SonarQube Cloud NOT_VERIFIED
- independent human release authority required
- Production remains NO-GO

Therefore this vNext branch is an architecture upgrade branch only until the new components have independent evidence.
