# NEXUS-OMNI ULTRA Governance V1

This layer converts the supplied NEXUS-OMNI ULTRA v14.0 prompt concept into a governed CK-NEXUS capability surface.

## Core rule

A prompt is not runtime authority.

Persona wording, slash commands, module counts, confidence percentages, agent counts, sales automation, research capability, external integrations, self-healing, self-improvement, memory, formal verification, and production readiness must never be reported as active merely because they appear in a system prompt.

Every command is resolved through `UltraCapabilityRegistry` and may report only one of these states:

- `READY_VERIFIED` — verified development evidence exists and a non-mutation executor is available.
- `VERIFIED_NO_EXECUTOR` — verification exists but no live executor is connected.
- `IMPLEMENTED_UNVERIFIED` — code exists but current evidence is insufficient.
- `SIMULATED` — conversational/model-assisted behavior only.
- `NOT_AVAILABLE` — no supported capability is registered.
- `BLOCKED` — governance explicitly prohibits execution.

## Safety corrections to the supplied ULTRA prompt

The following claims are not accepted as runtime facts without evidence:

- `34+ modules — all systems online`
- `28 agents`
- `50+ APIs`
- `66 skills`
- `security 100%`
- `resilience 100%`
- `accuracy 100%`
- `fairness 100%`
- `confidence 98%`
- `humanity 90%`
- `auto-sell 24/7`
- `self-evolving / infinite evolution`
- persistent memory not backed by an authorized memory store
- live research without a connected research tool
- live formal proof without a theorem-prover executor

They may be used as product goals or UI copy only when clearly labeled as targets, simulated modes, or unverified claims.

## Reasoning boundary

`/think` may provide concise rationale, assumptions, alternatives, and decision summaries. It must not promise or expose private chain-of-thought traces as a runtime feature.

## Mutation boundary

Commands that can perform external writes, sales actions, deployment, account creation, payment, destructive chaos, or production mutation require CK-NEXUS governance and an authorized executor. Prompt text alone cannot grant that authority.

## Current development commands

The initial registry includes `/status`, `/help`, `/chaos`, `/formal`, `/evidence`, `/code`, `/research`, `/sales`, and `/think`. Their status is determined at runtime by the registry rather than by the persona prompt.

## Production boundary

This Post-P0 layer is development-only. It does not alter PR #14, Q10/Q11/Q12, production authority, or release readiness.
