# CK-NEXUS Learning Consolidation Blueprint

Status: DESIGN_ONLY / NOT_IMPLEMENTED

This blueprint implements Work Package 12 of the CK-NEXUS Final Integrated Order. It reuses the safety and evidence semantics of the existing AGNES Triad Learning Consolidator without importing an incomplete dependency graph into canonical main.

## Objective

Learning in CK-NEXUS means converting measured outcomes and feedback into a reviewable candidate improvement. It does not mean silently changing policy, prompts, tools, models, permissions, release state or Production configuration.

The default lifecycle is:

```text
Observation
  -> measured outcome
  -> feedback/failure evidence
  -> candidate delta
  -> PROPOSE / BLOCK / QUARANTINE
  -> isolated experiment
  -> benchmark/security review
  -> independent verification
  -> human-controlled adoption decision
```

## Reused AGNES semantics

The existing Triad Learning candidate provides important controls that should remain canonical requirements:

- decisions: `PROPOSE`, `BLOCK`, `QUARANTINE`
- semantic fingerprint to reject duplicate learning deltas
- contradiction and rejection thresholds
- minimum measured-ratio and score thresholds
- evidence binding to source pulse/window/receipt digests
- supersession that preserves prior history
- hash-chained ledger verification
- verification ceiling `MEASURED_NOT_VERIFIED`
- `independent_verification_required = true`
- `experiment_required = true`
- `adoption_allowed = false`
- `auto_activation_allowed = false`
- `external_action_allowed = false`
- `production_mutation_allowed = false`

These semantics are reused as requirements, not claimed as canonical runtime availability. The current consolidator depends on Triad Pulse components not proven present on canonical main as a complete dependency chain.

## Learning input classes

### Explicit user feedback

Examples: accepted/rejected answer, correction, preferred output format, task-success confirmation.

Rules:

- feedback scope must be explicit
- sensitive personal attributes must not be inferred merely for optimization
- negative feedback is evidence, not permission to bypass safety or authority
- user preferences cannot override security/governance policy

### Runtime outcome evidence

Examples: test results, benchmark metrics, task completion, tool failure, latency, retry exhaustion.

Rules:

- bind to exact task/run/subject identifiers
- preserve measured vs inferred distinction
- do not learn from a success claim that lacks the required evidence

### Failure memory

A failure record should include:

- normalized failure class
- component/capability
- exact subject/version where available
- triggering conditions without raw secrets
- symptom and root-cause status
- remediation attempted
- verification outcome
- semantic/failure fingerprint
- recurrence count
- supersession link when the diagnosis changes

Failure memory is used to prevent repeated mistakes and guide experiments. It does not directly patch Production.

### External knowledge/research signals

External research may propose a capability delta but remains untrusted until benchmark/security/verification stages are complete.

## Proposal contract

A learning proposal should contain at minimum:

- `learning_id`
- subject/version binding
- capability affected
- normalized insight
- expected measurable delta
- semantic fingerprint
- source evidence references/digests
- current baseline metrics
- proposed experiment
- success/failure thresholds
- security impact
- rollback strategy
- verification ceiling
- independent-verification requirement
- adoption/activation authority flags fixed to false by default

## Decision rules

### PROPOSE

Allowed only when:

- the candidate is novel relative to known fingerprints
- required evidence is complete enough for an experiment
- contradiction/rejection thresholds are not exceeded
- measured-quality thresholds are met
- no protected authority boundary is requested

PROPOSE means "eligible for experiment", not "approved for adoption".

### BLOCK

Use when:

- candidate duplicates an existing delta
- measured evidence is below threshold
- required provenance is missing
- experiment cannot be made reproducible
- expected delta has no measurable acceptance criterion

### QUARANTINE

Use when:

- material contradiction exists
- evidence integrity is uncertain
- source/provenance conflicts exist
- the candidate would alter protected authority or security boundaries
- observed behavior may indicate poisoning or unsafe feedback manipulation

Quarantine preserves evidence for review and prevents silent retrial loops.

## Experiment boundary

Experiments must run in an isolated Development Lane with:

- exact baseline and candidate subject IDs
- deterministic/reproducible fixture where possible
- bounded resources and time
- no Production credentials
- no external side effects unless separately approved
- rollback or disposable environment
- benchmark output stored as evidence

A candidate that cannot be evaluated safely remains blocked.

## Benchmark and acceptance

Every capability delta must define relevant metrics. Depending on the feature these may include:

- correctness
- precision/recall
- retrieval quality
- latency
- memory/CPU/storage use
- failure rate
- recovery time
- security-regression count
- reproducibility
- cost/resource efficiency

Adoption requires a material capability or quality improvement without unacceptable regression. "Different" is not sufficient.

## Failure-memory loop

```text
Failure observed
  -> fingerprint
  -> search prior failure memory
  -> if duplicate: reuse prior diagnosis/remediation evidence
  -> if new: root-cause candidate
  -> isolated remediation experiment
  -> regression test
  -> security review
  -> proposal for consolidation
```

Repeated failures should increase priority for root-cause investigation, not weaken retry or safety limits.

## Knowledge Fabric integration

Knowledge Fabric and Learning Consolidation remain separate authorities:

- Knowledge Fabric stores provenance-rich claims and memory-write proposals.
- Learning Consolidation proposes behavioral/capability deltas.
- Claim/Governance Registry tracks evidence and verification states.
- none of these layers may approve itself.

A learning proposal may reference Knowledge Fabric claim IDs. Durable learning memory should be written only through the existing consent/retention/provenance boundary.

## Independent verification matrix

Independent verification is mandatory before canonical adoption for deltas that:

- change authorization or approval behavior
- change secret/credential handling
- add a new external connector or execution capability
- change memory retention or cross-tenant behavior
- change evidence generation or verification
- alter model/tool routing with security impact
- change recovery/retry/idempotency behavior
- affect release or Production controls

Lower-risk presentation-only changes may use normal independent code review according to project policy, but still cannot self-approve.

## Protected non-learning domains

Learning automation must never directly mutate:

- Q10/Q11/Q12 verification state
- Production GO/NO-GO
- owner sign-off records
- independent-review attestation
- security policy authority
- user/tenant permissions
- credential scopes or secret values
- frozen evidence subjects
- audit/evidence history

Any requested change to these domains becomes a separately governed proposal.

## Poisoning and feedback-abuse controls

Before implementation, tests must cover:

- repeated malicious feedback attempting to weaken controls
- prompt injection presented as learning feedback
- duplicate/replayed evidence
- forged benchmark outcomes
- cross-tenant feedback contamination
- contradictory signals
- popularity/frequency mistaken for truth
- source trust score mistaken for verification
- poisoned failure-memory entries

## Ledger requirements

The future implementation should preserve append-only learning history with:

- monotonic sequence
- subject binding
- candidate digest
- semantic fingerprint
- previous-record digest
- supersession reference
- independently recomputable head digest

Editing or deleting prior records must not be the normal update mechanism. New evidence should supersede prior conclusions.

## Dependency reconciliation before implementation

Before moving from this blueprint to code:

1. identify the canonical home for Triad Pulse/Memory dependencies
2. prove they are not duplicated by current AGNES/Cognitive Runtime branches
3. define adapter boundaries to Knowledge Fabric and Claim Registry
4. reuse existing failure-memory work where stronger than a new implementation
5. establish benchmark fixtures
6. complete security threat model

Only then should implementation be proposed.

## Definition of Done for the blueprint

This WP12 design is complete when:

- proposal/block/quarantine semantics are specified
- feedback and failure-memory inputs are specified
- experiment and benchmark gates are specified
- protected authority boundaries are explicit
- independent-verification triggers are explicit
- dependency reconciliation requirements are documented

This document itself creates no learning runtime, no autonomous adoption, and no Production evidence.
