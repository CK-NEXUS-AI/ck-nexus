# CK-NEXUS Universal Command Intake & Execution Protocol V1

Status: Post-P0 development candidate.
Authority: CK-NEXUS.
Production effect: none.
Q10/Q11/Q12 effect: none.

## Purpose

Every user command, agent task, automation request, and development action must
be classified before execution. The protocol prevents immediate action without
intent understanding, reuse checks, risk classification, evidence planning,
and the controls appropriate to the task.

The protocol is a pre-execution contract and completion gate. It is not a new
runtime authority and does not replace the existing orchestration controller,
AGNES execution kernel, Master Controller, approval registry, credential
broker, sandbox, or evidence system.

## Six invariants

1. Search before Solve.
2. Reuse before Build.
3. Measure before Claim.
4. Verify before Trust.
5. Learn before Repeat.
6. Never let the worker approve itself.

## Intensity levels

### L0 Minimal

For simple read-only questions.

Required minimum:
- intent understanding,
- task classification,
- risk classification,
- authority check,
- completion check,
- report delta.

### L1 Standard

For ordinary bounded work.

Adds:
- recall prior work,
- search existing implementation,
- issue/PR/branch lookup,
- reuse decision,
- execution plan,
- success criteria,
- tool and assistant routing,
- smallest reversible change,
- observation,
- functional check,
- truthful status,
- queue update.

### L2 Complex

For complex research, architecture, code changes, bug fixes, and evidence work.

Adds when relevant:
- fresh-source research,
- official-source priority,
- multi-query and multi-language expansion,
- knowledge-gap and coverage checks,
- evidence-independence and contradiction checks,
- at least three alternative approaches,
- independent specialist perspectives,
- comparison/benchmark,
- baseline,
- evidence plan,
- rollback,
- isolation,
- stuck detection,
- regression/security/resource checks,
- independent critic,
- evidence binding,
- problem/attempt/solution/knowledge learning.

### L3 High Impact

For security authority, infrastructure high impact, deployment, production,
credentials, destructive work, purchases, and equivalent critical actions.

L3 uses the full applicable protocol and requires human approval according to
policy. A model, provider, crawler, agent, or worker cannot grant itself
authority.

## Risk levels

- R0 READ_ONLY
- R1 SAFE_REVERSIBLE
- R2 MUTABLE_REVERSIBLE
- R3 HIGH_IMPACT
- R4 CRITICAL

Risk can be elevated by explicit signals, task class, environment, or policy.
An explicit caller hint cannot lower a higher inferred risk.

Production environment, destructive actions, credential access, purchases,
security-authority changes, and Q-gate effects are always R4.

## Reuse decision

Before a new implementation, one explicit decision is required:

- REUSE
- EXTEND
- REPAIR
- REPLACE
- MERGE
- ARCHIVE
- DO_NOT_USE
- NEW_IMPLEMENTATION_REQUIRED

NEW_IMPLEMENTATION_REQUIRED is blocked if the existing implementation search
was not completed.

## Search-before-Solve

For tasks requiring current or external knowledge, the protocol requires:

1. freshness check,
2. official or primary sources first,
3. multiple query angles,
4. multilingual search when relevant,
5. knowledge-gap detection,
6. coverage measurement,
7. evidence-lineage independence check,
8. contradiction detection.

Global Knowledge Filtering V1 may classify retrieved candidates as ACCEPT,
QUARANTINE, or REJECT and emit search-expansion directives. Passing that
filter never promotes a source or claim to VERIFIED.

## Alternatives

L2 and L3 work requires at least three materially different approaches before
execution. The intent is not to generate cosmetic variants. Typical categories
are repair, replacement, and architectural bypass/redesign.

Specialists should receive different roles rather than duplicate prompts:
research, architecture, implementation, security, operations, and adversarial
review.

## Pre-execution gate

Execution is blocked when required preparation is incomplete.

Examples:
- no reuse decision,
- new implementation without existing-work search,
- fewer than three alternatives for L2/L3,
- missing baseline,
- missing evidence plan,
- rollback not ready,
- isolation not ready,
- required human approval missing.

## Completion gate

A worker cannot serve as its own independent reviewer.

Completion checks:
- functional behavior,
- regression,
- security,
- resource impact where relevant,
- independent critic,
- required human review,
- exact evidence binding,
- truthful status,
- learning persistence,
- queue update,
- delta report.

Passing technical checks alone does not automatically produce VERIFIED.
For complex work without explicit external verification, the highest automatic
state is MEASURED_NOT_VERIFIED.

## Reuse of existing CK-NEXUS components

The protocol must compose existing controls rather than create parallel
authorities:

- orchestration PatternSelector and GuardrailEvaluator,
- Master Controller V1 for deterministic tool routing,
- AGNES policy and execution kernel,
- sticky human approvals,
- Credential Broker,
- isolated workspace/sandbox execution,
- Knowledge Persistence V2 for durable problem/attempt learning,
- Collaborative Development Framework for multi-agent work,
- Global Knowledge filtering/search expansion,
- append-only evidence and learning ledgers.

## 47-step lifecycle

The canonical step IDs are encoded in
`creator_app.command_protocol.ProtocolStep` and preserve the owner-defined
sequence from intent understanding through final delta reporting.

Not every command executes all 47 steps. Required steps are selected by task,
risk, current-information needs, mutability, and intensity. This keeps simple
read-only work fast while preserving full controls for complex and high-impact
work.

## Safety

This implementation is development-only. It does not authorize production
deployment, Q10/Q11/Q12 promotion, payment, credential disclosure, destructive
actions, evidence fabrication, self-approval, or bypass of existing policy.
