from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
    ProviderRouteError,
    ProviderRouter,
    ProviderRouterPolicy,
)


@dataclass
class FakeProvider:
    name: str
    kind: ProviderKind
    output: str = "ok"
    available: bool = True
    fail: bool = False
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    calls: int = 0

    def is_available(self) -> bool:
        return self.available

    async def invoke(self, prompt: str) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"provider detail must stay private: {prompt}")
        return self.output


@pytest.mark.asyncio
async def test_local_first_is_deterministic_and_falls_back_to_cloud() -> None:
    cloud = FakeProvider("cloud", ProviderKind.CLOUD, output="cloud result")
    local = FakeProvider("local", ProviderKind.LOCAL, output="local result", fail=True)
    mock = FakeProvider("mock", ProviderKind.MOCK, output="mock result")
    router = ProviderRouter(
        [cloud, local, mock],
        policy=ProviderRouterPolicy(local_first=True, max_attempts=3),
    )

    selected = await router.route("hello")

    assert selected.provider == "mock"
    assert selected.output == "mock result"
    assert selected.attempts == 2
    assert selected.degraded is True
    assert local.calls == 1
    assert mock.calls == 1
    assert cloud.calls == 0


@pytest.mark.asyncio
async def test_cloud_can_be_disabled_and_capabilities_are_enforced() -> None:
    local = FakeProvider(
        "local",
        ProviderKind.LOCAL,
        capabilities=ProviderCapabilities(features=frozenset({"text"})),
    )
    cloud = FakeProvider(
        "cloud",
        ProviderKind.CLOUD,
        capabilities=ProviderCapabilities(features=frozenset({"text", "tools"})),
    )
    router = ProviderRouter([local, cloud], policy=ProviderRouterPolicy(allow_cloud=False))

    with pytest.raises(ProviderRouteError) as caught:
        await router.route("needs tools", required_capabilities={"tools"})

    assert caught.value.code == "NO_PROVIDER"
    assert caught.value.attempts == 0
    assert local.calls == 0
    assert cloud.calls == 0


@pytest.mark.asyncio
async def test_attempts_are_bounded_and_failures_open_circuit() -> None:
    now = [100.0]
    first = FakeProvider("first", ProviderKind.LOCAL, fail=True)
    second = FakeProvider("second", ProviderKind.LOCAL, fail=True)
    third = FakeProvider("third", ProviderKind.CLOUD, fail=True)
    router = ProviderRouter(
        [first, second, third],
        policy=ProviderRouterPolicy(
            max_attempts=2,
            failure_threshold=1,
            circuit_cooldown_seconds=10,
        ),
        clock=lambda: now[0],
    )

    with pytest.raises(ProviderRouteError) as caught:
        await router.route("secret-looking input should not appear in the error")

    assert caught.value.code == "DEGRADED"
    assert caught.value.attempts == 2
    assert first.calls == 1
    assert second.calls == 1
    assert third.calls == 0
    status = {item.name: item for item in router.statuses()}
    assert status["first"].circuit_open is True
    assert status["second"].circuit_open is True
    assert "secret-looking" not in str(caught.value)


@pytest.mark.asyncio
async def test_open_circuit_is_skipped_then_recovers_after_cooldown() -> None:
    now = [1.0]
    local = FakeProvider("local", ProviderKind.LOCAL, fail=True)
    cloud = FakeProvider("cloud", ProviderKind.CLOUD, output="fallback")
    router = ProviderRouter(
        [local, cloud],
        policy=ProviderRouterPolicy(failure_threshold=1, circuit_cooldown_seconds=5),
        clock=lambda: now[0],
    )

    first = await router.route("one")
    second = await router.route("two")
    assert first.provider == "cloud"
    assert second.provider == "cloud"
    assert local.calls == 1

    now[0] = 6.0
    local.fail = False
    local.output = "recovered"
    recovered = await router.route("three")

    assert recovered.provider == "local"
    assert recovered.output == "recovered"
    assert local.calls == 2
    assert router.statuses()[0].consecutive_failures == 0


def test_provider_names_must_be_unique_and_policy_bounds_are_validated() -> None:
    one = FakeProvider("same", ProviderKind.LOCAL)
    two = FakeProvider("same", ProviderKind.CLOUD)
    with pytest.raises(ValueError, match="unique"):
        ProviderRouter([one, two])
    with pytest.raises(ValueError, match="max_attempts"):
        ProviderRouterPolicy(max_attempts=0)
