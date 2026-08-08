from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Protocol, runtime_checkable


class ProviderKind(StrEnum):
    LOCAL = "local"
    MOCK = "mock"
    CLOUD = "cloud"


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Capabilities advertised by a provider without performing a live probe."""

    features: frozenset[str] = frozenset()
    models: tuple[str, ...] = ()

    def supports(self, required: Iterable[str]) -> bool:
        return frozenset(required).issubset(self.features)


@runtime_checkable
class ProviderAdapter(Protocol):
    """Small provider seam used by the router; concrete adapters own API details."""

    name: str
    kind: ProviderKind
    capabilities: ProviderCapabilities

    def is_available(self) -> bool: ...

    async def invoke(self, prompt: str) -> str: ...


@dataclass(frozen=True, slots=True)
class ProviderRouterPolicy:
    local_first: bool = True
    allow_cloud: bool = True
    max_attempts: int = 3
    failure_threshold: int = 2
    circuit_cooldown_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.circuit_cooldown_seconds < 0:
            raise ValueError("circuit_cooldown_seconds cannot be negative")


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: str
    kind: ProviderKind
    output: str
    attempts: int
    degraded: bool


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    name: str
    kind: ProviderKind
    available: bool
    circuit_open: bool
    consecutive_failures: int
    capabilities: ProviderCapabilities


class ProviderRouteError(RuntimeError):
    """Safe routing error that never includes provider exception or credential text."""

    def __init__(self, code: str, message: str, *, attempts: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.attempts = attempts


@dataclass(slots=True)
class _Circuit:
    consecutive_failures: int = 0
    open_until: float = 0.0


class ProviderRouter:
    """Deterministic, bounded provider selection with a small circuit breaker.

    A provider is attempted at most once per ``route`` call. The global attempt
    limit bounds work even when many adapters are registered. Circuit state is
    intentionally in-memory for this single-process R5 seam; durable/shared
    state can replace it later without changing the adapter contract.
    """

    def __init__(
        self,
        providers: Iterable[ProviderAdapter],
        *,
        policy: ProviderRouterPolicy | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._providers = tuple(providers)
        self.policy = policy or ProviderRouterPolicy()
        self._clock = clock
        self._circuits = {provider.name: _Circuit() for provider in self._providers}
        names = [provider.name for provider in self._providers]
        if len(names) != len(set(names)):
            raise ValueError("provider names must be unique")

    def statuses(self) -> tuple[ProviderStatus, ...]:
        now = self._clock()
        statuses: list[ProviderStatus] = []
        for provider in self._providers:
            circuit = self._circuits[provider.name]
            self._close_expired_circuit(circuit, now)
            statuses.append(
                ProviderStatus(
                    name=provider.name,
                    kind=provider.kind,
                    available=provider.is_available(),
                    circuit_open=circuit.open_until > now,
                    consecutive_failures=circuit.consecutive_failures,
                    capabilities=provider.capabilities,
                )
            )
        return tuple(statuses)

    async def route(
        self,
        prompt: str,
        *,
        required_capabilities: Iterable[str] = (),
    ) -> ProviderSelection:
        required = frozenset(required_capabilities)
        candidates = self._ordered_candidates(required)
        if not candidates:
            raise ProviderRouteError(
                "NO_PROVIDER",
                "No eligible AI provider is currently available for this request.",
            )

        attempts = 0
        failures = 0
        for provider in candidates:
            if attempts >= self.policy.max_attempts:
                break
            attempts += 1
            try:
                output = await provider.invoke(prompt)
            except Exception:
                failures += 1
                self._record_failure(provider.name)
                continue

            self._record_success(provider.name)
            return ProviderSelection(
                provider=provider.name,
                kind=provider.kind,
                output=output,
                attempts=attempts,
                degraded=failures > 0,
            )

        raise ProviderRouteError(
            "DEGRADED",
            "Eligible AI providers are degraded or failed within the bounded attempt limit.",
            attempts=attempts,
        )

    def _ordered_candidates(
        self, required_capabilities: frozenset[str]
    ) -> list[ProviderAdapter]:
        now = self._clock()
        eligible: list[tuple[int, ProviderAdapter]] = []
        for index, provider in enumerate(self._providers):
            circuit = self._circuits[provider.name]
            self._close_expired_circuit(circuit, now)
            if circuit.open_until > now:
                continue
            if provider.kind is ProviderKind.CLOUD and not self.policy.allow_cloud:
                continue
            if not provider.capabilities.supports(required_capabilities):
                continue
            if not provider.is_available():
                continue
            eligible.append((index, provider))

        if not self.policy.local_first:
            return [provider for _, provider in eligible]

        def preference(item: tuple[int, ProviderAdapter]) -> tuple[int, int]:
            index, provider = item
            local_tier = 0 if provider.kind in {ProviderKind.LOCAL, ProviderKind.MOCK} else 1
            return local_tier, index

        return [provider for _, provider in sorted(eligible, key=preference)]

    def _record_failure(self, provider_name: str) -> None:
        circuit = self._circuits[provider_name]
        circuit.consecutive_failures += 1
        if circuit.consecutive_failures >= self.policy.failure_threshold:
            circuit.open_until = self._clock() + self.policy.circuit_cooldown_seconds

    def _record_success(self, provider_name: str) -> None:
        circuit = self._circuits[provider_name]
        circuit.consecutive_failures = 0
        circuit.open_until = 0.0

    @staticmethod
    def _close_expired_circuit(circuit: _Circuit, now: float) -> None:
        if circuit.open_until and circuit.open_until <= now:
            circuit.consecutive_failures = 0
            circuit.open_until = 0.0


ProviderInvoke = Callable[[str], Awaitable[str]]
