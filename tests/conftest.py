from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("ck-nexus")
    group.addoption(
        "--mock-provider",
        action="store_true",
        default=False,
        help="Force vendor-neutral mock provider mode.",
    )
    group.addoption(
        "--live-provider",
        action="store_true",
        default=False,
        help="Explicitly allow live provider tests.",
    )
    group.addoption(
        "--attack-mode",
        action="store_true",
        default=False,
        help="Enable security attack-regression assertions.",
    )
    group.addoption(
        "--chaos-level",
        type=int,
        choices=(0, 1, 2, 3),
        default=0,
        help="Select bounded chaos test level 0-3.",
    )


def pytest_configure(config: pytest.Config) -> None:
    for marker in (
        "gen6_1: Gen 6.1 runtime-contract tests",
        "gen6_2: Gen 6.2 elastic-swarm tests",
        "gen6_3: Gen 6.3 cognitive-memory tests",
        "security: security regression test",
        "chaos: chaos/simulation test",
        "slow: test expected to exceed normal unit-test latency",
        "manual: requires explicit operator execution",
        "live_provider: may call a real provider and is disabled by default",
    ):
        config.addinivalue_line("markers", marker)

    mock = config.getoption("--mock-provider")
    live = config.getoption("--live-provider")
    if mock and live:
        raise pytest.UsageError("--mock-provider and --live-provider are mutually exclusive")
    if live:
        os.environ["CKNEXUS_TEST_PROVIDER_MODE"] = "live"
    else:
        os.environ["CKNEXUS_TEST_PROVIDER_MODE"] = "mock"
        os.environ.setdefault("CKNEXUS_MOCK_AI", "true")


@pytest.fixture(scope="session")
def ck_provider_mode(pytestconfig: pytest.Config) -> str:
    if pytestconfig.getoption("--live-provider"):
        return "live"
    return "mock"


@pytest.fixture(scope="session")
def ck_attack_mode(pytestconfig: pytest.Config) -> bool:
    return bool(pytestconfig.getoption("--attack-mode"))


@pytest.fixture(scope="session")
def ck_chaos_level(pytestconfig: pytest.Config) -> int:
    return int(pytestconfig.getoption("--chaos-level"))
