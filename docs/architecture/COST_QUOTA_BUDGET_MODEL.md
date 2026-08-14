# Cost, Quota, and Budget Model

Status: architecture contract.

## Principle

Cost and quota influence routing but never override policy, authorization, privacy, evidence requirements or semantic correctness.

## Separate concepts

- `price_observation`: provider price or estimated unit cost at an observed time;
- `usage_observation`: measured tokens/requests/storage/compute/etc.;
- `quota_observation`: provider/account allowance and remaining headroom when observable;
- `budget`: CK-NEXUS owner/tenant/task spending ceiling;
- `credit`: provider-specific commercial construct, not a portable token;
- `cost_estimate`: pre-execution estimate with uncertainty.

## Routing

Capability resolver may optimize cost among already-authorized eligible implementations. Hard constraints include maximum task/tenant budget and `free_only`/local-only policy when explicitly configured. If no eligible lane satisfies hard constraints, fail closed.

## Forbidden behavior

- create new accounts/keys to continue after quota exhaustion;
- rotate identities/keys to evade provider limits or terms;
- distribute one provider credential/credit to another service;
- claim a free tier is unlimited;
- silently switch private/local data to an external provider because it is cheaper.

## Budget reservation

Impactful or potentially expensive tasks may reserve a bounded budget before execution. Parallel/council modes account for aggregate expected cost. Retries/fallback consume the same task budget unless policy explicitly grants more.

## Observations

Cost/quota observations include source, provider/account reference in redacted form, currency/unit, measured/estimated flag, observed_at, fresh_until and confidence when estimated. Unknown quota is not treated as unlimited headroom.

## Alerts

Alert examples: task budget nearing ceiling, tenant daily/monthly budget burn, provider quota low, abnormal cost per verified task, runaway retry/council cost, stale price observation.

## Buyer safety

Commercial builds expose default ceilings and an owner-facing cost policy. Billing/paid resource creation remains an explicit owner action.
