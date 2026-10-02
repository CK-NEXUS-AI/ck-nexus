# CK-NEXUS · Governance Coverage Contract

> Status: **DESIGNED**. This defines what it means for a mutation path to be covered. It is the contract P0.1 (Gateway) and P0.2 (Scanner) must jointly satisfy.

## 1. Coverage verdicts

- `MEDIATED` — a Gateway decision exists on the path and can DENY.
- `UNMEDIATED` — the path is reachable without a Gateway decision.
- `UNKNOWN` — no runtime evidence. **Not SAFE. Not APPROVED.**

## 2. Required coverage chain

```
agent_id
  → lease_id
  → policy_version
  → approval_id
  → mutation_surface
  → resource
  → gateway_decision
  → execution
  → post_receipt
```

Any missing link is a coverage gap.

## 3. Gateway decision binding

Every decision MUST carry:

```
decision_id, agent_id, lease_id,
policy_version, policy_hash,
action, resource, scope, context_hash,
verdict, expiry, timestamp, signer
```

Verdicts: `DENY | ESCALATE | WARN | TRANSFORM | ALLOW`.

## 4. Composite-path rule

A composite path is covered only if every mutation leaf is covered. Entry-only mediation does not prove leaf coverage.

## 5. Authority inheritance rule

A sub-agent spawned under lease L must either:
- inherit a narrowed copy of L, or
- obtain its own lease.

Unbounded inherited authority is not accepted.

## 6. Deferred-execution rule

Scheduled/background mutation MUST re-check approval validity at fire time. Expired approval ⇒ DENY.

## 7. Admission pipeline

```
DISCOVERED → STATIC VERIFIED → RUNTIME EXECUTED
           → COVERAGE VERIFIED → ADMITTED
```

## 8. Explicit non-acceptance

- Gateway on entry, unmediated on exit.
- MCP invocation mediated while downstream API mutation is blind.
- Plugin adds a surface without re-scan.
- Sub-agent escalates authority.
- Deferred job fires after approval expiry.

## 9. Current state

```
P0.1 Gateway           = DESIGNED
P0.2 Scanner           = DESIGNED
Runtime coverage       = UNKNOWN
Production admission   = NO-GO
```
