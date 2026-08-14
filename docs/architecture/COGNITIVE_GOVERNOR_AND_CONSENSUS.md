# Cognitive Governor and Consensus

Status: architecture contract.

## Principle

CK-NEXUS is the cognitive operating system; external/local models are replaceable cognitive workers. A model response is a proposal/observation, not authority to mutate systems.

## Pipeline

`Intent -> Context Policy -> Cognitive Governor -> Capability/Model Resolution -> Worker Lane(s) -> Normalization -> Grounding/Critique -> Consensus -> Final Composer -> Verification -> Memory/Evidence`

Consequential tool calls proposed by workers return to Trust + AGNES for separate authorization/execution.

## Worker roles

Semantic roles may include researcher, coder, architect, planner, critic, security reviewer, factual verifier, creative worker, summarizer and final composer. Roles are capability requirements, not permanently tied to one vendor/model.

## Modes

- `SINGLE_BEST`: one best eligible worker.
- `FALLBACK`: primary worker plus ordered alternatives on classified failure.
- `PARALLEL`: independent workers produce candidates for aggregation.
- `COUNCIL`: role-diverse workers contribute specialized evidence/opinions.
- `DEBATE`: bounded critique/revision rounds under a stopping rule.
- `SHADOW`: non-authoritative worker evaluated without affecting user result/side effects.

Mode selection respects budget, latency deadline, data policy, risk and evidence needs. Expensive multi-worker execution is not automatic for trivial tasks.

## Consensus

Consensus is not majority vote alone. Aggregation considers contract validity, grounding/evidence, task fit, confidence calibration, contradiction severity, historical evaluation, policy compliance, freshness, latency and cost.

When high-quality workers materially disagree, CK-NEXUS preserves uncertainty or asks for clarification rather than manufacturing confidence.

## Final composer

The composer may synthesize only from eligible candidate outputs/evidence. It cannot erase verifier vetoes, invent missing citations, or convert an unsupported claim into supported state.

## Safety boundary

A cognitive worker never receives raw cross-provider credentials. Tool access is represented by bounded semantic grants/proposals. Prompt injection or tool instructions found in retrieved content are untrusted data unless explicitly authorized as instructions by policy/context.
