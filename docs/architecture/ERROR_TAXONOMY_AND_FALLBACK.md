# Error Taxonomy and Fallback Matrix

Status: architecture contract.

## Goal

Failures must be machine-classified before retry/fallback. Blind retry is forbidden because it can duplicate messages, payments, tickets, deployments, or other side effects.

## Canonical classes

- `AUTH_MISSING`: no authorized credential/connection.
- `AUTH_EXPIRED`: reauthentication/refresh required.
- `AUTH_SCOPE_INSUFFICIENT`: connection exists but grant is too narrow.
- `POLICY_DENIED`: policy or risk rule denied execution.
- `APPROVAL_REQUIRED`: human approval is required.
- `RATE_LIMITED`: provider throttling.
- `QUOTA_EXHAUSTED`: authorized account quota exhausted.
- `BUDGET_EXCEEDED`: CK budget hard limit reached.
- `TIMEOUT`: deadline exceeded with no confirmed outcome.
- `TRANSIENT_NETWORK`: temporary transport failure.
- `PROVIDER_DEGRADED`: provider health/service degradation.
- `INVALID_INPUT`: request contract failed.
- `INVALID_OUTPUT`: provider result failed output validation.
- `GROUNDING_INSUFFICIENT`: evidence/citation requirement failed.
- `CONFLICT`: multiple authoritative observations disagree.
- `DUPLICATE`: idempotency/replay duplicate detected.
- `PARTIAL_SIDE_EFFECT`: some but not all intended mutations committed.
- `UNKNOWN_COMMIT_STATE`: request outcome cannot be determined.
- `PERMANENT_PROVIDER_ERROR`: non-retryable provider failure.
- `INTERNAL_BUG`: CK-NEXUS implementation defect.
- `SECURITY_VETO`: security verifier/council veto.

## Retry policy

Retry is permitted only when the operation's retry-safety declaration and commit state allow it. Exponential backoff with jitter is recommended for transport/rate limits. Retry count and elapsed time are bounded.

`UNKNOWN_COMMIT_STATE` must reconcile first. Never retry a payment, external message, destructive mutation, or production control operation while commit state is unknown.

## Fallback policy

Fallback may select another already-authorized eligible implementation when semantic equivalence and policy permit. It must preserve task constraints, data policy, side-effect grant, output contract, and evidence requirements.

Fallback must not:

- create a new account/key automatically;
- distribute a token to another provider;
- evade quotas/terms;
- downgrade required security/evidence;
- switch from local/private to external processing when data policy forbids it.

## Compensation

For sagas/partial side effects, compensation is a separately authorized capability. Compensation is not assumed to be a perfect rollback; its outcome is independently verified and recorded.

## Escalation

After retry/fallback budget is exhausted, emit an incident/event with task state, classified failure, attempted lanes, commit-state confidence, recommended owner action, and evidence references.
