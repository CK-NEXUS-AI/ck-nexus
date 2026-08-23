from __future__ import annotations

import json

from creator_app.credentials.credit_telemetry import (
    CreditSnapshot,
    CreditTelemetryFabric,
    OpenAICostBudgetAdapter,
    OpenRouterCreditsAdapter,
)
from creator_app.credentials.free_fallback_keypool import FreeFallbackKeyPool
from creator_app.credentials.llm_keypool import LlmKeySpec


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class FakeAdapter:
    def __init__(self, snapshot: CreditSnapshot) -> None:
        self.provider = snapshot.provider
        self.snapshot = snapshot

    def collect(self) -> CreditSnapshot:
        return self.snapshot


def _pool(tmp_path, provider: str = "paid") -> FreeFallbackKeyPool:
    spec = LlmKeySpec(
        id=provider,
        env_var="TEST_CREDIT_KEY",
        base_url="https://example.invalid/v1",
        model="test-model",
        free=False,
    )
    return FreeFallbackKeyPool(
        [spec],
        remaining_threshold_pct=85,
        policy_state_path=str(tmp_path / "policy.json"),
    )


def test_known_credit_at_85_activates_free_only(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_CREDIT_KEY", "secret")
    pool = _pool(tmp_path)
    adapter = FakeAdapter(
        CreditSnapshot(
            provider="paid",
            state="KNOWN",
            source="test.authoritative",
            remaining_pct=85.0,
            basis="provider_credit",
        )
    )
    fabric = CreditTelemetryFabric(
        pool,
        adapters=[adapter],
        evidence_path=str(tmp_path / "telemetry.jsonl"),
    )

    fabric.collect_once()

    assert pool.free_only_mode is True
    assert "test.authoritative" in (pool.free_only_reason or "")


def test_known_credit_above_85_does_not_activate(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_CREDIT_KEY", "secret")
    pool = _pool(tmp_path)
    adapter = FakeAdapter(
        CreditSnapshot(
            provider="paid",
            state="KNOWN",
            source="test.authoritative",
            remaining_pct=85.01,
        )
    )
    fabric = CreditTelemetryFabric(pool, adapters=[adapter], evidence_path="")

    fabric.collect_once()

    assert pool.free_only_mode is False


def test_unknown_credit_never_guesses_or_activates(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_CREDIT_KEY", "secret")
    pool = _pool(tmp_path)
    adapter = FakeAdapter(
        CreditSnapshot(
            provider="paid",
            state="UNKNOWN",
            source="unsupported",
            detail="no authoritative source",
        )
    )
    fabric = CreditTelemetryFabric(pool, adapters=[adapter], evidence_path="")

    report = fabric.collect_once()

    assert report["paid"].remaining_pct is None
    assert pool.free_only_mode is False
    assert fabric.status()["unknown_policy"] == "DO_NOT_GUESS"


def test_openrouter_credit_endpoint_normalizes_remaining(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_MANAGEMENT_KEY", "management-secret")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(
            {"data": {"total_credits": 100.0, "total_usage": 15.0}}
        ),
    )

    snapshot = OpenRouterCreditsAdapter().collect()

    assert snapshot.state == "KNOWN"
    assert snapshot.remaining_pct == 85.0
    assert snapshot.basis == "provider_credit"


def test_openrouter_without_management_key_is_unknown(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_MANAGEMENT_KEY", raising=False)

    snapshot = OpenRouterCreditsAdapter().collect()

    assert snapshot.state == "UNKNOWN"
    assert snapshot.remaining_pct is None


def test_openai_costs_normalize_against_explicit_budget(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("CKNEXUS_OPENAI_MONTHLY_BUDGET_USD", "100")
    payload = {
        "data": [
            {
                "results": [
                    {"amount": {"value": 10.0, "currency": "usd"}},
                    {"amount": {"value": 5.0, "currency": "usd"}},
                ]
            }
        ]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse(payload),
    )

    snapshot = OpenAICostBudgetAdapter().collect()

    assert snapshot.state == "KNOWN"
    assert snapshot.used_amount == 15.0
    assert snapshot.total_amount == 100.0
    assert snapshot.remaining_pct == 85.0
    assert snapshot.basis == "configured_budget"


def test_openai_without_admin_key_or_budget_is_unknown(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    monkeypatch.delenv("CKNEXUS_OPENAI_MONTHLY_BUDGET_USD", raising=False)

    snapshot = OpenAICostBudgetAdapter().collect()

    assert snapshot.state == "UNKNOWN"
    assert snapshot.remaining_pct is None


def test_unsupported_configured_provider_is_recorded_unknown(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_CREDIT_KEY", "secret")
    pool = _pool(tmp_path, provider="groq")
    fabric = CreditTelemetryFabric(pool, adapters=[], evidence_path="")

    report = fabric.collect_once()

    assert report["groq"].state == "UNKNOWN"
    assert report["groq"].source == "unsupported_provider"
    assert pool.free_only_mode is False


def test_evidence_contains_no_credential_material(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_CREDIT_KEY", "super-secret-value")
    pool = _pool(tmp_path)
    evidence = tmp_path / "telemetry.jsonl"
    adapter = FakeAdapter(
        CreditSnapshot(
            provider="paid",
            state="KNOWN",
            source="test.authoritative",
            remaining_pct=90.0,
        )
    )
    fabric = CreditTelemetryFabric(pool, adapters=[adapter], evidence_path=str(evidence))

    fabric.collect_once()

    raw = evidence.read_text(encoding="utf-8")
    assert "super-secret-value" not in raw
    assert '"credential_material_logged": false' in raw
