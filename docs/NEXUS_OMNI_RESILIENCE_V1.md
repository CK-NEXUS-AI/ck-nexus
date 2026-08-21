# NEXUS-OMNI Resilience & Reliability V1

Development-only Post-P0 reliability layer.

## Enforced principles

- Chaos is deterministic and adapter-driven; core code never invokes host `pkill`, `iptables`, `tc`, `docker kill`, or disk-filling commands.
- Fault execution requires both sandbox attestation and an explicit execution grant.
- Evidence records are append-only JSONL, hash-linked, fsync'd, and persist digests rather than raw payloads.
- Deterministic state uses canonical serialization and hash-derived choices, not mutable global RNG state.
- Provider mocks use one typed vendor-neutral contract with success, error, and timeout scenarios.
- The existing Test Standards workflow enforces Ruff, per-test timeout, scoped coverage >=80%, attack regression, bounded chaos simulations, and evidence artifacts.
- Lean 4 remains the formal verification authority for the invariants currently modeled in this development stack.

## Non-claims

- This layer does not prove all CK-NEXUS behavior mathematically.
- Development coverage >=80% is scoped to the governed contracts listed in the workflow; repository-wide >=80% is not claimed.
- GitHub server-side branch protection/rulesets are not changed by this layer.
- These artifacts do not alter Q10/Q11/Q12, PR #14, or production authority.

## Directory mapping

- `creator_app/core/` — reliability contracts
- `tests/unit/` — isolated deterministic/evidence/mock tests
- `tests/integration/` — composed reliability flow tests
- `tests/security/` — attack-contract regression
- `tests/chaos/` — bounded failure simulation
- `formal/` — Lean 4 invariants
- `scripts/` — evidence/report automation
