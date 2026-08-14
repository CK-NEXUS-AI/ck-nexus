# CK-NEXUS Architecture Invariants

Status: normative architecture constraints.

1. Every executable ability is represented as a semantic Capability.
2. Every replaceable implementation exposes a versioned Contract/Manifest.
3. Impactful side effects route through Trust + AGNES; apps/models/providers cannot bypass them.
4. Credentials are brokered/leased; raw cross-provider token distribution is forbidden.
5. Hard policy/tenant/data-sovereignty constraints outrank routing scores.
6. External/model claims are observations/candidates until validated with provenance/evidence.
7. Retry of an uncertain side effect waits for reconciliation when commit state is unknown.
8. Important state is durable; in-memory coordination is non-production unless explicitly safe.
9. Events are replayable; business side effects must remain idempotent/reconciled.
10. Evidence binds the exact subject it proves and has explicit freshness/invalidation semantics.
11. `NOT_RUN`, `BLOCKED`, stale or insufficient evidence never becomes PASS.
12. Memory retrieval filters tenant/policy before semantic ranking.
13. New skills/plugins/code cannot self-promote; quarantine/evaluation/canary precede stable lifecycle.
14. Model tool calls are proposals, not side-effect authority.
15. Cost/quota optimization cannot create accounts/keys, evade limits or weaken privacy/security.
16. UI visibility is not authorization; server-side policy applies to every control command.
17. Approval is scoped/bound/expiring and cannot be laundered into broader authority.
18. Connector lifecycle, authorization, health and capability verification are separate states.
19. Backup existence does not prove restorability; recovery requires isolated verified drill evidence.
20. Production remains fail-closed until Q01-Q16 required evidence yields GO.
