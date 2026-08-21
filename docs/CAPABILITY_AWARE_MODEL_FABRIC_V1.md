# CK-NEXUS Capability-Aware Model Fabric V1

Development-only, provider-neutral routing layer for selecting AI models by verified capability evidence rather than static brand rankings.

## Why

Model leadership changes quickly. CK-NEXUS must not hard-code claims such as "provider X is always best at coding" or "model Y is always the smartest". Routing decisions must be reproducible, explainable, evidence-backed, and replaceable.

## Capability dimensions

- coding
- system_engineering
- reasoning
- abstract_reasoning
- math
- multimodal
- research
- tool_use
- latency
- cost_efficiency

## Evidence rules

A capability score is usable only when its evidence is current and verified. Evidence can be provider-published, independent, or CK-NEXUS internal evaluation. Independent and internal evidence may carry higher routing weight, but no evidence source can bypass verification.

Expired evidence is ignored. Future-dated evidence is invalid. If a task requires a minimum score and no model satisfies it, routing fails closed.

## Routing

A task declares weighted capability requirements. The router computes a deterministic weighted score from current verified evidence. The top model is the primary candidate; remaining models are ordered fallbacks. When possible, CK-NEXUS chooses an independent verifier from a different provider to reduce provider monoculture and correlated failure.

## Example task profiles

- System coding: coding 0.55, system_engineering 0.25, reasoning 0.20
- Deep reasoning: reasoning 0.60, abstract_reasoning 0.25, math 0.15
- Fast balanced assistant: reasoning 0.35, latency 0.35, cost_efficiency 0.30
- Multimodal analysis: multimodal 0.50, reasoning 0.30, tool_use 0.20

These are policy examples, not permanent model rankings.

## Boundaries

- No provider SDK calls are added by this layer.
- No vendor is designated as permanently best.
- No benchmark score is hard-coded into runtime code.
- No production mutation is authorized.
- PR #14 and Q10/Q11/Q12 are untouched.
- Development CI evidence does not equal Production Ready.
