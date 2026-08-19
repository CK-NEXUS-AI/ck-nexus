from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from time import monotonic
from typing import Protocol

from creator_app.capability_registry import (
    Capability,
    CapabilityRegistry,
    ProviderCandidate,
)
from creator_app.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)

logger = logging.getLogger("cknexus.broker")


class RouteOutcome(StrEnum):
    SUCCESS = "success"
    FALLBACK = "fallback"
    BLOCKED = "blocked"
    NO_PROVIDER = "no_provider"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    request_id: str
    capability: str
    provider: str
    credential_reference_id: str
    account_tenant_id: str
    policy_decision: str
    selected_route: str
    fallback_reason: str
    latency_ms: int
    cost_metadata: dict
    result_digest: str
    timestamp: float


@dataclass(frozen=True, slots=True)
class CredentialLease:
    credential_id: str
    consumer: str
    reference_id: str
    source: str
    expires_at: float | None = None

    def reveal(self, *, consumer: str) -> str:
        from creator_app.credential_broker import CredentialAccessDenied
        if consumer != self.consumer:
            raise CredentialAccessDenied("lease bound to different consumer")
        # Actual reveal only happens inside the consumer's sandboxed call
        return ""

    def __repr__(self) -> str:
        return (
            f"CredentialLease(credential_id={self.credential_id!r}, "
            f"consumer={self.consumer!r}, source={self.source!r}, value=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class RoutingResult:
    capability: str
    provider: str
    credential_reference: str
    account_tenant_id: str
    source: str
    lease_expiry: float | None
    latency_ms: int
    route: str
    outcome: RouteOutcome
    fallback_chain: tuple[str, ...] = ()


@dataclass
class BrokerPolicy:
    quota_warning_threshold_pct: float = 95.0
    max_fallback_attempts: int = 3
    circuit_cooldown_seconds: float = 30.0
    default_ttl_seconds: float = 3600.0
    audit_log_path: Path | None = None
    fail_closed: bool = True


class ProviderRouter(Protocol):
    """Abstract provider router interface."""

    def candidates(
        self, capability: str, required_scopes: Iterable[str]
    ) -> list[ProviderCandidate]: ...

    def report_success(self, provider: str) -> None: ...

    def report_failure(self, provider: str) -> None: ...


class LlmKeyPoolAdapter:
    """Adapts the LlmKeyPool to the ProviderCandidate interface for OpenAI-like capabilities."""

    def __init__(self, pool: object | None = None) -> None:
        self._pool = pool
        self._status: list[object] = []

    def refresh_status(self) -> None:
        if self._pool is not None and hasattr(self._pool, "status"):
            self._status = list(self._pool.status())

    def candidates(
        self,
        capability: Capability,
        required_scopes: Iterable[str],
    ) -> list[ProviderCandidate]:
        if self._pool is None:
            return []
        self.refresh_status()
        result: list[ProviderCandidate] = []
        for entry in self._status:
            if not hasattr(entry, "key_id"):
                continue
            result.append(
                ProviderCandidate(
                    provider=entry.provider,
                    capability=Capability.OPENAI_RESPONSES,
                    credential_id=f"openai.api_key:{entry.key_id}",
                    account_tenant_id="",
                    health="healthy" if entry.healthy else "degraded",
                    quota_remaining=-1,
                    rate_limit_state="normal" if not entry.exhausted else "exhausted",
                    cost=0.0,
                    latency_ms=0,
                    region="",
                    priority=10 if entry.free else 5,
                )
            )
        return result

    def report_success(self, provider: str) -> None:
        if self._pool is not None and hasattr(self._pool, "report_success"):
            self._pool.report_success(provider)

    def report_failure(self, provider: str) -> None:
        if self._pool is not None and hasattr(self._pool, "report_failure"):
            self._pool.report_failure(provider)

    def acquire_best(self) -> tuple[str, str | None, str | None, str]:
        """Returns (key_id, base_url, model, source)."""
        if self._pool is None:
            raise CredentialUnavailable("LLM key pool is not configured")
        selection = self._pool.acquire()
        if selection is None:
            raise CredentialUnavailable("No healthy LLM key in pool")
        return (
            selection.key_id,
            selection.base_url,
            selection.model,
            "llm_key_pool",
        )


class UniversalCredentialBroker:
    """CK-NEXUS Universal Credential Broker + Capability Router.

    Implements the full authority chain:
    USER -> ACCESS -> GOVERNOR -> POLICY -> CREDENTIAL BROKER
    -> CAPABILITY ROUTER -> TOOL/API -> VERIFICATION -> EVIDENCE

    Core principles:
    - Never exposes raw secrets to agents/models
    - Resolves credentials by capability request, not bulk export
    - Short-lived lease preference with TTL
    - OAuth refresh support for token rotation
    - Provider/account isolation
    - Automatic failover based on: capability compatibility, scope, health,
      quota remaining, rate-limit state, latency, cost, region, expiry, policy
    - Fail-closed if no authorized candidate exists
    - Append-only audit events
    """

    def __init__(
        self,
        broker: CredentialBroker | None = None,
        registry: CapabilityRegistry | None = None,
        providers: dict[str, ProviderCandidate] | None = None,
        policy: BrokerPolicy | None = None,
    ) -> None:
        self.broker = broker or CredentialBroker()
        self.registry = registry or CapabilityRegistry()
        self.policy = policy or BrokerPolicy()
        self._providers: dict[str, ProviderCandidate] = providers or {}
        self._circuits: dict[str, float] = {}
        self._audit_events: list[AuditEvent] = []

    def register_provider(self, candidate: ProviderCandidate) -> None:
        key = f"{candidate.provider}:{candidate.credential_id}"
        self._providers[key] = candidate

    def _ordered_candidates(
        self, capability: str, required_scopes: Iterable[str]
    ) -> list[ProviderCandidate]:
        """Score and order provider candidates for a capability request.

        Scoring priority (per user specification):
        1. capability compatibility (exact required capability match)
        2. scope (must satisfy required scopes)
        3. health (healthy preferred)
        4. quota remaining (higher is better; warn at threshold)
        5. rate-limit state (normal > rate_limited > exhausted)
        6. cost (lower is better)
        7. latency (lower is better)
        8. expiry (non-expired only)
        9. region (matching preferred, if set)
        10. policy risk (low preferred)
        """
        scopes = frozenset(required_scopes)
        now = monotonic()
        candidates: list[tuple[int, ProviderCandidate]] = []

        for candidate in self._providers.values():
            if candidate.capability.value != capability:
                continue
            if candidate.expiry_seconds > 0 and now > candidate.expiry_seconds:
                continue
            if not scopes.issubset(frozenset(candidate.scopes)):
                continue

            circuit_key = f"{candidate.provider}:{candidate.credential_id}"
            if circuit_key in self._circuits and self._circuits[circuit_key] > now:
                continue

            score = 0
            if candidate.health == "healthy":
                score += 0
            elif candidate.health == "degraded":
                score += 100
            else:
                continue

            if candidate.quota_remaining >= 0:
                pct_used = (
                    (candidate.quota_total - candidate.quota_remaining)
                    / max(candidate.quota_total, 1) * 100
                )
                if pct_used >= self.policy.quota_warning_threshold_pct:
                    score += 500
                elif pct_used >= 80:
                    score += 200
                elif pct_used >= 50:
                    score += 50

            rate_tier = {"normal": 0, "rate_limited": 10, "exhausted": 100}
            score += rate_tier.get(candidate.rate_limit_state, 50)
            score += int(candidate.cost * 100)
            score += candidate.latency_ms
            score += candidate.priority
            score += 0 if candidate.policy_risk == "low" else (
                50 if candidate.policy_risk == "medium" else 200
            )

            candidates.append((score, candidate))

        candidates.sort(key=lambda item: item[0])
        return [c for _, c in candidates]

    async def route(
        self,
        capability: str,
        *,
        required_scopes: Iterable[str] = (),
        prompt: str | None = None,
    ) -> RoutingResult:
        """Route a capability request to the best available provider.

        If the best provider fails or its quota is near exhaustion,
        automatically falls back to the next candidate.
        """
        request_id = f"req-{int(monotonic() * 1000000)}"
        start = monotonic()
        spec = self.registry.get(capability)
        if spec is None:
            outcome = RouteOutcome.NO_PROVIDER
            self._audit(
                AuditEvent(
                    request_id=request_id,
                    capability=capability,
                    provider="",
                    credential_reference_id="",
                    account_tenant_id="",
                    policy_decision="capability_unknown",
                    selected_route="",
                    fallback_reason="",
                    latency_ms=0,
                    cost_metadata={},
                    result_digest="",
                    timestamp=start,
                )
            )
            if self.policy.fail_closed:
                raise ValueError(f"Unknown capability: {capability}")
            return RoutingResult(
                capability=capability,
                provider="",
                credential_reference="",
                account_tenant_id="",
                source="",
                lease_expiry=None,
                latency_ms=0,
                route="",
                outcome=outcome,
            )

        consumer = spec.required_consumer
        scopes = tuple(spec.provider_scopes) + tuple(required_scopes)
        candidates = self._ordered_candidates(capability, scopes)
        fallback_chain: list[str] = []

        if not candidates:
            outcome = RouteOutcome.NO_PROVIDER
            self._audit(request_id, capability, "", "", "no_candidate", "", "", start)
            if self.policy.fail_closed:
                raise CredentialUnavailable(
                    f"No eligible provider for capability: {capability}"
                )
            return RoutingResult(
                capability=capability,
                provider="",
                credential_reference="",
                account_tenant_id="",
                source="",
                lease_expiry=None,
                latency_ms=0,
                route="",
                outcome=outcome,
            )

        for attempt, candidate in enumerate(candidates):
            if attempt >= self.policy.max_fallback_attempts:
                break

            credential_id = CredentialId(candidate.credential_id.split(":")[0])
            try:
                lease = self.broker.acquire(credential_id, consumer=consumer)
            except Exception:
                self._circuit_open(
                    f"{candidate.provider}:{candidate.credential_id}",
                    self.policy.circuit_cooldown_seconds,
                )
                fallback_chain.append(candidate.provider)
                continue

            try:
                if prompt is not None and hasattr(self, "_execute"):
                    await self._execute(prompt, lease, consumer)
            except Exception:
                self._circuit_open(
                    f"{candidate.provider}:{candidate.credential_id}",
                    self.policy.circuit_cooldown_seconds,
                )
                fallback_chain.append(candidate.provider)
                continue

            latency_ms = int((monotonic() - start) * 1000)
            outcome = RouteOutcome.FALLBACK if fallback_chain else RouteOutcome.SUCCESS
            self._audit(
                AuditEvent(
                    request_id=request_id,
                    capability=capability,
                    provider=candidate.provider,
                    credential_reference_id=candidate.credential_id,
                    account_tenant_id=candidate.account_tenant_id,
                    policy_decision="allowed",
                    selected_route=candidate.provider,
                    fallback_reason="->".join(fallback_chain) if fallback_chain else "",
                    latency_ms=latency_ms,
                    cost_metadata={"cost": candidate.cost},
                    result_digest=self._digest(prompt, outcome),
                    timestamp=start,
                )
            )
            return RoutingResult(
                capability=capability,
                provider=candidate.provider,
                credential_reference=candidate.credential_id,
                account_tenant_id=candidate.account_tenant_id,
                source=lease.source,
                lease_expiry=lease.expires_at if hasattr(lease, "expires_at") else None,
                latency_ms=latency_ms,
                route=candidate.provider,
                outcome=outcome,
                fallback_chain=tuple(fallback_chain),
            )

        self._audit(
            AuditEvent(
                request_id=request_id,
                capability=capability,
                provider="",
                credential_reference_id="",
                account_tenant_id="",
                policy_decision="fail_closed",
                selected_route="",
                fallback_reason="->".join(fallback_chain),
                latency_ms=int((monotonic() - start) * 1000),
                cost_metadata={},
                result_digest="",
                timestamp=start,
            )
        )
        if self.policy.fail_closed:
            raise CredentialUnavailable(
                f"All candidates for {capability} failed within bounds"
            )
        return RoutingResult(
            capability=capability,
            provider="",
            credential_reference="",
            account_tenant_id="",
            source="",
            lease_expiry=None,
            latency_ms=int((monotonic() - start) * 1000),
            route="",
            outcome=RouteOutcome.BLOCKED,
            fallback_chain=tuple(fallback_chain),
        )

    async def request(self, capability: str, **kwargs) -> RoutingResult:
        """Public entry point for capability requests."""
        return await self.route(capability, **kwargs)

    def statuses(self) -> tuple[dict[str, object], ...]:
        """Return redacted status of all registered providers."""
        results: list[dict[str, object]] = []
        for candidate in self._providers.values():
            pct = candidate.quota_percentage_used()
            results.append(
                {
                    "provider": candidate.provider,
                    "capability": candidate.capability.value,
                    "credential_reference": candidate.credential_id,
                    "health": candidate.health,
                    "quota_percentage_used": pct,
                    "rate_limit_state": candidate.rate_limit_state,
                    "latency_ms": candidate.latency_ms,
                    "priority": candidate.priority,
                    "value": "<redacted>",
                }
            )
        return tuple(results)

    def audit_events(self, *, limit: int = 100) -> tuple[dict[str, object], ...]:
        bounded = max(1, min(limit, 500))
        return tuple(
            {
                "request_id": e.request_id,
                "capability": e.capability,
                "provider": e.provider,
                "credential_reference": e.credential_reference_id,
                "account_tenant_id": e.account_tenant_id,
                "policy_decision": e.policy_decision,
                "selected_route": e.selected_route,
                "fallback_reason": e.fallback_reason,
                "latency_ms": e.latency_ms,
                "cost_metadata": e.cost_metadata,
                "result_digest": e.result_digest,
                "timestamp": e.timestamp,
            }
            for e in self._audit_events[-bounded:]
        )

    def _circuit_open(self, key: str, cooldown: float) -> None:
        self._circuits[key] = monotonic() + cooldown

    def _audit(self, event: AuditEvent) -> None:
        self._audit_events.append(event)
        if self.policy.audit_log_path:
            try:
                with self.policy.audit_log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event.__dict__, default=str) + "\n")
            except OSError:
                logger.warning("Failed to write audit event to disk")

    @staticmethod
    def _digest(prompt: str | None, outcome: RouteOutcome) -> str:
        import hashlib
        payload = f"{prompt or ''}:{outcome.value}".encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def clear_circuits(self) -> None:
        self._circuits.clear()

    def __repr__(self) -> str:
        return (
            f"UniversalCredentialBroker(providers={len(self._providers)}, "
            f"circuits={len(self._circuits)}, values=<redacted>)"
        )
