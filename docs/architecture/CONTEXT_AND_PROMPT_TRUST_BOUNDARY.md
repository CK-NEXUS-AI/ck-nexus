# Context and Prompt Trust Boundary

Status: architecture contract.

## Sources

Context may come from owner/system policy, current user instructions, application state, memory, knowledge/RAG, connectors, web/public sources, provider outputs and tool results. These sources have different authority.

## Rule

Data retrieved from email, web pages, documents, tickets, repositories or model output is untrusted content, not automatically executable instruction. Embedded instructions cannot override system/owner policy, authorization or the user's explicit goal.

## Context compiler

The compiler selects minimal task-relevant context, labels source/trust/data classification, enforces tenant boundaries, applies redaction, tracks provenance and fits budget/context constraints.

## Secret boundary

Raw secrets are excluded from general model context. When a provider/tool operation needs credentials, CredentialBroker injects them at the transport boundary rather than prompt context where possible.

## Memory

Memories are context candidates with validation/freshness/retention state. `user preference` is distinguishable from `factual claim` and `external instruction`.

## Tool proposals

Model/tool-call output is parsed against schemas and policy. Free-form text cannot directly become shell/SQL/provider mutation without typed compilation, authorization and safety controls.

## Injection response

Suspicious instructions can be ignored, redacted, quarantined, surfaced as a security signal or sent to a security verifier depending on risk. The system should still extract legitimate user-requested data when safe rather than treating all adversarial-looking content as unusable.
