from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MockOutcome(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class MockRequest(BaseModel):
    operation: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
    scenario: str = "default"


class MockResponse(BaseModel):
    outcome: MockOutcome
    status_code: int = Field(ge=100, le=599)
    data: dict[str, object] = Field(default_factory=dict)
    error: str | None = None
    latency_ms: int = Field(default=0, ge=0)
    provider: str = "mock-provider"


class StandardMockProvider:
    """Deterministic vendor-neutral provider used by contract tests."""

    def __init__(self) -> None:
        self._scenarios: dict[str, MockResponse] = {
            "default": MockResponse(
                outcome=MockOutcome.SUCCESS,
                status_code=200,
                data={"ok": True},
            ),
            "error": MockResponse(
                outcome=MockOutcome.ERROR,
                status_code=503,
                error="mock provider unavailable",
            ),
            "timeout": MockResponse(
                outcome=MockOutcome.TIMEOUT,
                status_code=504,
                error="mock provider timeout",
                latency_ms=30000,
            ),
        }

    def register(self, name: str, response: MockResponse) -> None:
        if not name:
            raise ValueError("scenario name must not be empty")
        self._scenarios[name] = response.model_copy(deep=True)

    def execute(self, request: MockRequest) -> MockResponse:
        response = self._scenarios.get(request.scenario)
        if response is None:
            raise ValueError(f"unknown mock scenario: {request.scenario}")
        return response.model_copy(deep=True)
