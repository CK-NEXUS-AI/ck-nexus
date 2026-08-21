# CK-NEXUS Gen 6.4 — Research + Formal Verification V1

Status: Post-P0 development only. Not production evidence.

## Parent authority

Gen 6.4 is stacked on the reconciled Gen 6.3 memory-learning line. The parent must have exact-head green CK-NEXUS CI, Universal System Post-P0 CI, and Security Attack Regression evidence before this layer is considered development-integrable.

## Contracts

- `deep_research.py`: bounded iterative research, evidence-required iterations, unresolved-gap continuation and external-write denial.
- `citation_graph.py`: digest-only claim/source relationships, independent-publisher quorum and contradiction-dominant verification.
- `hypothesis_tournament.py`: independent evaluator quorum, required dissent, safety-veto dominance and evidence-bound evolutionary candidates.
- `formal_verification.py`: exact-subject machine-checker receipt contract with pinned versions, deterministic execution and network-off policy.
- `research_artifacts.py`: reproducible source/environment/input/output digests and evaluator-fleet quorum receipts.

## Non-capabilities

This layer does not itself browse the web, call model/provider APIs, run scientific databases, execute Lean/SMT/TLA+, mutate repositories or activate production changes. Provider/checker execution belongs to separately governed adapters and must provide real evidence receipts.

## Fail-closed invariants

- missing evidence blocks promotion
- verified contradictions dominate claim verification
- safety veto blocks hypothesis eligibility
- floating checker/provider versions are not reproducible
- formal receipts are bound to the exact subject digest
- evolved candidates never auto-activate
- production activation remains false

## Production boundary

No PR #14 merge/change. No Q10/Q11/Q12 promotion. Production remains NO-GO.
