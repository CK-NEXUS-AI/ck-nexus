# Uncertainty and Conflict Resolution

Status: architecture contract.

## Uncertainty ledger

CK-NEXUS records unresolved uncertainty that can affect a decision/result: missing evidence, stale source, conflicting observations, unknown external commit state, low-confidence extraction, ambiguous user intent and model disagreement.

## Types

- `EPISTEMIC`: insufficient/contradictory knowledge.
- `OPERATIONAL`: runtime/health/commit state unknown.
- `INTENT`: user goal/target ambiguous.
- `POLICY`: authority/policy applicability unresolved.
- `MEASUREMENT`: insufficient eval/telemetry samples.

## Resolution actions

Possible actions: retrieve stronger source, run verifier, compare independent workers, ask user, safe live probe, reconcile external state, wait for freshness window, quarantine candidate, or abstain.

## Confidence

Confidence is scoped to a claim/decision and method. Do not combine arbitrary model confidence values as calibrated probabilities. Aggregation stores method and evidence.

## Conflicts

For factual/operational conflicts, source authority and freshness outrank model eloquence. For design/creative conflicts, preserve alternatives/tradeoffs rather than force factual-style resolution.

## High-impact rule

High-impact execution cannot rely on unresolved uncertainty above policy tolerance. `UNKNOWN_COMMIT_STATE` and uncertain target identity are hard blocks for unsafe retry/new mutation.
