# CK-NEXUS Controlled Self-Expansion Pipeline

Status: SPEC_ONLY
Version: 0.1

Self-expansion means CK-NEXUS can detect a missing capability, search for an existing trusted implementation, or generate a candidate implementation in isolation. It does NOT mean unrestricted self-modification.

## Goals

- close capability gaps with minimal manual integration work
- prefer reuse over code generation
- preserve provider/connector neutrality
- enforce contracts before registration
- require evidence before canary
- prevent self-generated code from silently entering trusted production paths

## Pipeline

```text
Capability Gap Detected
-> Normalize Gap Specification
-> Search Capability Registry
-> Search Installed Plugins
-> Search Approved Marketplace Sources
-> Evaluate Candidates
-> if usable candidate exists: stage candidate
-> else: generate implementation proposal
-> isolated workspace
-> implement adapter/plugin
-> compile/lint/type-check
-> unit tests
-> contract tests
-> integration simulation
-> security scan
-> dependency/supply-chain checks
-> policy review
-> evidence bundle
-> human/change-control approval when required
-> register CANDIDATE
-> staging canary
-> verify metrics/postconditions
-> promote to STABLE only through release governance
```

## Gap specification

A capability gap should be represented as structured data:
- requested semantic capability
- expected input/output contracts
- risk/side-effect class
- data classification
- latency target
- budget target
- online/offline constraints
- acceptable providers or prohibited providers
- required evidence level
- tenant/user scope

The gap detector must distinguish `missing capability` from `temporarily unhealthy capability`, `policy denied`, `quota exhausted`, and `credential unavailable`.

## Candidate preference order

1. already installed and trusted capability
2. installed but disabled capability that can safely be re-evaluated
3. approved first-party CK-NEXUS plugin
4. approved external plugin/connector
5. generated adapter over a documented API
6. generated local implementation

A generated implementation is the last resort, not the default.

## Isolated development workspace

Self-generated code must run outside trusted runtime authority. Isolation requirements SHOULD include:
- no production credentials
- no production write network paths
- disposable filesystem/worktree
- bounded CPU/memory/time
- explicit dependency allow/deny policy
- recorded source provenance
- network egress policy
- generated-code marker

## Verification lanes

### Build lane
- format/lint
- compile/type-check
- dependency resolution
- import validation

### Contract lane
- manifest validation
- input schema tests
- output schema tests
- error contract tests
- timeout/cancellation behavior
- idempotency behavior where applicable

### Security lane
- secret scan
- static security analysis
- dependency vulnerability audit
- unsafe network/URL handling checks
- credential-boundary tests
- permission escalation tests
- sandbox escape checks where relevant

A true deep-security gate must use the designated deep-security mechanism; weaker scans may be supplemental but cannot impersonate that gate.

### Behavior lane
- deterministic fixtures where possible
- mocked external APIs
- negative/error cases
- retry/fallback cases
- postcondition verification

### Governance lane
- risk classification
- required approval class
- data classification compatibility
- quota/cost policy
- tenant boundary
- kill-switch compliance

## Registration states

`PROPOSED -> BUILT -> LOCALLY_VERIFIED -> SECURITY_REVIEWED -> CONTRACT_VERIFIED -> CANDIDATE -> CANARY -> STABLE`

Any state may transition to `QUARANTINED`, `REVOKED`, or `DEPRECATED`.

No component may self-write its own state to `STABLE`.

## Canary rules

Canary execution must:
- use isolated/non-production targets unless explicitly approved
- have bounded traffic/task percentage
- have automatic rollback criteria
- compare error rate, latency, evidence quality, cost, and semantic task success against baseline
- emit complete evidence

## Automated repair boundary

Repair automation may:
- restart an isolated worker
- refresh an owner-authorized expiring credential lease
- retry transient failures
- switch to another already-authorized capability
- rollback a reversible canary
- rebuild disposable caches/indexes

Repair automation may NOT silently:
- create accounts
- create new API keys
- broaden OAuth scopes
- rotate across identities to bypass quotas
- purchase credits/resources
- disable security checks
- alter canonical production code
- delete/restore production data destructively

## Learning from expansion

The system may store:
- which gap patterns recur
- which candidates succeeded
- contract-test history
- provider reliability
- canary outcomes
- cost/latency/evidence quality

Learning updates routing priors and recommendations, but learned scores do not override hard policy or approval requirements.

## Promotion rule

Promotion is a governance act, not an AI confidence score. A capability becomes trusted only when its required evidence, security, staging/canary, and release gates are satisfied for the exact candidate version.