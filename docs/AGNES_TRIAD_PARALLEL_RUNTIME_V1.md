# AGNES Triad Parallel Intelligence Fabric v1

Status: IMPLEMENTED_NOT_EXECUTED (development only)

## Purpose

Run three role-specialized agents in parallel while preserving CK-NEXUS authority boundaries:

- A / BUILDER: proposes alternatives and revisions.
- B / CRITIC: raises evidence-backed objections and risks.
- C / EVIDENCE EVALUATOR: measures candidate claims but cannot self-promote them to VERIFIED.
- GOVERNOR: owns policy, budget, pause/stop, and execution authority.

## Source of truth

The runtime is event/artifact driven, not transcript driven. Dialogue is useful context, but system state is represented by append-only TriadEvent records and CandidateArtifact objects.

## 15/20 Adaptive Pulse

- 00-15 minutes: ACTIVE_PARALLEL
- 15-35 minutes: DISCOVERY_CONSOLIDATION
- minute 35: CHECKPOINT
- after three no-progress cycles: IDLE/backoff

The pulse is a scheduling policy, not permission to create model calls when no meaningful work exists.

## Claim states

DISCOVERED -> PROPOSED -> DISCUSSED -> MEASURED_NOT_VERIFIED -> VERIFIED
                                         
                                         -> REJECTED

MEASURED is never equivalent to VERIFIED. Independent verification must use a verifier identity different from the producer identity.

## Debate rules

- Critic is not required to invent an objection.
- Consensus is optional; unresolved candidates may be branched and measured independently.
- Repeated argument count is not a success metric.
- Evidence gain, resolved risk, measurable improvement, and uncertainty reduction are preferred progress signals.

## Authority boundaries

Triad components may propose, critique, measure, search, test in approved sandboxes, and create evidence artifacts. They may not merge, deploy, mutate production, expose credentials, spend money, modify Governor policy, or self-verify production claims.

## Next implementation steps

1. Triad Memory State Machine
2. Evidence Evaluator adapter to existing ExecutionReceipt / Claim Registry
3. NoProgressGuard binding and BRANCH / GOVERNOR_ARBITRATE transitions
4. Durable checkpoint binding for cycle restore
5. Event-driven dashboard projector
