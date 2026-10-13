from __future__ import annotations

import json
from collections.abc import Callable

from creator_app.credentials.anthropic_credit_telemetry import AnthropicCostBudgetAdapter


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _cost_payload(amount_cents: str = "1500", *, has_more: bool = False) -> dict:
    return {
        "data": [
            {
                "starting_at": "2026-08-01T00:00:00Z",
                "ending_at": "2026-08-02T00:00:00Z",
                "results": [{"amount": amount_cents, "currency": "USD"}],
            }
        ],
        "has_more": has_more,
        "next_page": "page-cost" if has_more else None,
    }


def _usage_payload(*, priority_tokens: int = 0, has_more: bool = False) -> dict:
    results = []
    if priority_tokens:
        results.append(
            {
                "uncached_input_tokens": priority_tokens,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
                "cache_creation": {},
                "server_tool_use": {"web_search_requests": 0},
            }
        )
    return {
        "data": [
            {
                "starting_at": "2026-08-01T00:00:00Z",
                "ending_at": "2026-08-02T00:00:00Z",
                "results": results,
            }
        ],
        "has_more": has_more,
        "next_page": "page-usage" if has_more else None,
    }


def _sequence_urlopen(payloads: list[dict]) -> tuple[Callable[..., FakeResponse], list[str]]:
    remaining = list(payloads)
    urls: list[str] = []

    def open_url(request, timeout):
        urls.append(request.full_url)
        return FakeResponse(remaining.pop(0))

    return open_url, urls


def test_anthropic_missing_admin_key_or_budget_is_unknown_without_network(monkeypatch) -> None:
    called = False

    def unexpected_call(request, timeout):
        nonlocal called
        called = True
        return FakeResponse({})

    monkeypatch.delenv("ANTHROPIC_ADMIN_KEY", raising=False)
    monkeypatch.delenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", unexpected_call)

    snapshot = AnthropicCostBudgetAdapter().collect()

    assert snapshot.state == "UNKNOWN"
    assert snapshot.remaining_pct is None
    assert called is False


def test_anthropic_cost_budget_known_when_no_priority_usage(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", "100")
    open_url, urls = _sequence_urlopen([_cost_payload("1500"), _usage_payload()])
    monkeypatch.setattr("urllib.request.urlopen", open_url)

    snapshot = AnthropicCostBudgetAdapter().collect()

    assert snapshot.state == "KNOWN"
    assert snapshot.used_amount == 15.0
    assert snapshot.total_amount == 100.0
    assert snapshot.remaining_amount == 85.0
    assert snapshot.remaining_pct == 85.0
    assert snapshot.currency == "usd"
    assert len(urls) == 2
    assert "/v1/organizations/cost_report?" in urls[0]
    assert "/v1/organizations/usage_report/messages?" in urls[1]
    assert "service_tiers%5B%5D=priority" in urls[1]
    assert "service_tiers%5B%5D=priority_on_demand" in urls[1]


def test_anthropic_priority_usage_blocks_percentage(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", "100")
    open_url, _ = _sequence_urlopen(
        [_cost_payload("1500"), _usage_payload(priority_tokens=25)]
    )
    monkeypatch.setattr("urllib.request.urlopen", open_url)

    snapshot = AnthropicCostBudgetAdapter().collect()

    assert snapshot.state == "UNKNOWN"
    assert snapshot.used_amount == 15.0
    assert snapshot.total_amount == 100.0
    assert snapshot.remaining_pct is None
    assert "priority_tier_usage" in (snapshot.detail or "")


def test_anthropic_cost_pagination_is_summed(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", "100")
    first = _cost_payload("500", has_more=True)
    second = _cost_payload("1000", has_more=False)
    open_url, urls = _sequence_urlopen([first, second, _usage_payload()])
    monkeypatch.setattr("urllib.request.urlopen", open_url)

    snapshot = AnthropicCostBudgetAdapter().collect()

    assert snapshot.state == "KNOWN"
    assert snapshot.used_amount == 15.0
    assert snapshot.remaining_pct == 85.0
    assert "page=page-cost" in urls[1]


def test_anthropic_invalid_budget_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", "not-a-number")

    snapshot = AnthropicCostBudgetAdapter().collect()

    assert snapshot.state == "ERROR"
    assert snapshot.remaining_pct is None
    assert snapshot.detail == "invalid_budget"
