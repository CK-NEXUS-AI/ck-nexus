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

## 7. Evidence hierarchy

The following hierarchy prevents test results from being over-interpreted:

```
STATIC_DOCUMENTED
      ↓
LOCAL_EXECUTED
      ↓
REMOTE_EXECUTED
      ↓
RUNTIME_VERIFIED
      ↓
COVERAGE_VERIFIED
      ↓
PRODUCTION
```

A lower-level result MUST NOT be promoted into a higher-level verdict without evidence for the missing layer.

Examples:
- A documented `exec` tool is not proof that `exec` is enabled in the target runtime.
- A passing unit test is not proof of runtime mediation.
- A passing Docker/E2E lane is not proof that every external mutation leaf is mediated.
- A remote Testbox/Crabbox PASS is evidence for the exact command/SHA/lane that ran, not a blanket production certification.
- `OPENCLAW_TESTBOX_ALLOW_STALE=1` is diagnostic only and cannot be release evidence.
- Live-provider tests are out of scope unless the required credentials are intentionally provisioned through the approved secure runner; credentials must never appear in chat, source, or logs.

## 8. Test-lane selection rule

For this P0.2 discovery phase:

1. Prefer static source/docs inspection.
2. Use bounded local tests only when dependencies are already available and the source is trusted.
3. Use targeted Vitest via `node scripts/run-vitest.mjs <target>` for narrowly scoped evidence.
4. Use `pnpm test:changed` / `pnpm check:changed` only when the repository's local workflow permits them.
5. Route large distributed checks, Docker, E2E, live evidence, and cross-platform checks through the repository's prescribed remote infrastructure when required.
6. If the required remote provider is unavailable, report the limitation; do not silently substitute an equivalent-looking local heavy gate.
7. Stop/refresh stale Testbox leases when merge base, lockfile, package-manager inputs, wrapper, workflow, or target SHA changes.

## 9. Coverage acceptance rule

A surface can become `COVERAGE_VERIFIED` only when evidence demonstrates:

1. the surface is actually enabled;
2. the mutation enters the intended Gateway;
3. the Gateway decision is bound to the agent/lease/policy/approval context;
4. DENY prevents the mutation;
5. ALLOW executes only within the authorized scope;
6. composite downstream leaves remain mediated;
7. post-execution evidence/receipt is emitted;
8. repeated/deferred execution re-checks authority where applicable.

Anything less remains `UNKNOWN`, `UNMEDIATED`, or lower evidence status as appropriate.

## 10. Explicit non-acceptance

- Gateway on entry, unmediated on exit.
- MCP invocation mediated while downstream API mutation is blind.
- Plugin adds a surface without re-scan.
- Sub-agent escalates authority.
- Deferred job fires after approval expiry.
- Heavy local test substituted for a prescribed remote evidence lane without disclosure.
- Stale Testbox lease reused after its binding inputs changed.
- A passing test treated as blanket production certification.

## 11. Admission pipeline

```
DISCOVERED → STATIC VERIFIED → RUNTIME EXECUTED
           → COVERAGE VERIFIED → ADMITTED
```

## 12. Current state

```
P0.1 Gateway           = DESIGNED
P0.2 Scanner           = DESIGNED
Test evidence policy   = DESIGNED
Runtime coverage       = UNKNOWN
Production admission   = NO-GO
```
