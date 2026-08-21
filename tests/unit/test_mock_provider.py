import pytest

from creator_app.core.mock_provider import (
    MockOutcome,
    MockRequest,
    MockResponse,
    StandardMockProvider,
)


def test_default_mock_succeeds_deterministically() -> None:
    provider = StandardMockProvider()
    request = MockRequest(operation="health")

    first = provider.execute(request)
    second = provider.execute(request)

    assert first == second
    assert first.outcome == MockOutcome.SUCCESS
    assert first.provider == "mock-provider"


def test_mock_can_represent_error_and_timeout() -> None:
    provider = StandardMockProvider()

    error = provider.execute(MockRequest(operation="x", scenario="error"))
    timeout = provider.execute(MockRequest(operation="x", scenario="timeout"))

    assert error.outcome == MockOutcome.ERROR
    assert error.status_code == 503
    assert timeout.outcome == MockOutcome.TIMEOUT
    assert timeout.latency_ms == 30000


def test_custom_scenario_is_copied_not_shared() -> None:
    provider = StandardMockProvider()
    provider.register(
        "custom",
        MockResponse(
            outcome=MockOutcome.SUCCESS,
            status_code=200,
            data={"value": 1},
        ),
    )

    response = provider.execute(MockRequest(operation="x", scenario="custom"))
    response.data["value"] = 2
    again = provider.execute(MockRequest(operation="x", scenario="custom"))

    assert again.data["value"] == 1


def test_unknown_mock_scenario_fails_closed() -> None:
    provider = StandardMockProvider()
    with pytest.raises(ValueError):
        provider.execute(MockRequest(operation="x", scenario="unknown"))
