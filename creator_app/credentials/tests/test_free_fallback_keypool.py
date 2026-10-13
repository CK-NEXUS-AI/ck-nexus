from __future__ import annotations

from creator_app.credentials.free_fallback_keypool import FreeFallbackKeyPool
from creator_app.credentials.llm_keypool import LlmKeySpec


def _specs() -> list[LlmKeySpec]:
    return [
        LlmKeySpec(
            id="paid",
            env_var="TEST_PAID_KEY",
            base_url="https://paid.test/v1",
            model="paid-model",
            free=False,
        ),
        LlmKeySpec(
            id="free",
            env_var="TEST_FREE_KEY",
            base_url="https://free.test/v1",
            model="free-model",
            free=True,
        ),
    ]


def test_free_only_triggers_when_paid_remaining_reaches_85_percent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    state = tmp_path / "free-policy.json"
    pool = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        allow_remote_free=False,
        policy_state_path=str(state),
    )

    pool.report_quota_usage("paid", used=15, total=100)

    assert pool.free_only_mode is True
    assert pool.policy_status()["mode"] == "FREE_ONLY"
    assert pool.acquire() is None
    assert pool.free_fallback is True


def test_free_only_does_not_trigger_above_remaining_guard(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    pool = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        policy_state_path=str(tmp_path / "policy.json"),
    )

    pool.report_quota_usage("paid", used=14, total=100)

    assert pool.free_only_mode is False
    selection = pool.acquire()
    assert selection is not None
    assert selection.key_id == "paid"


def test_free_only_never_selects_paid_key_and_can_use_explicit_remote_free(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    pool = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        allow_remote_free=True,
        policy_state_path=str(tmp_path / "policy.json"),
    )

    pool.report_quota_usage("paid", used=15, total=100)
    selection = pool.acquire()

    assert selection is not None
    assert selection.key_id == "free"
    assert selection.free is True


def test_free_provider_quota_does_not_activate_paid_credit_guard(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    pool = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        policy_state_path=str(tmp_path / "policy.json"),
    )

    pool.report_quota_usage("free", used=100, total=100)

    assert pool.free_only_mode is False


def test_sticky_free_only_survives_restart(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    state = tmp_path / "free-policy.json"

    first = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        policy_state_path=str(state),
    )
    first.report_quota_usage("paid", used=15, total=100)
    assert first.free_only_mode is True

    restarted = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        policy_state_path=str(state),
    )

    assert restarted.free_only_mode is True
    assert restarted.acquire() is None


def test_explicit_operator_reset_clears_sticky_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_PAID_KEY", "paid-secret")
    monkeypatch.setenv("TEST_FREE_KEY", "free-secret")
    state = tmp_path / "free-policy.json"
    pool = FreeFallbackKeyPool(
        _specs(),
        remaining_threshold_pct=85,
        policy_state_path=str(state),
    )
    pool.report_quota_usage("paid", used=15, total=100)

    pool.reset_free_only()

    assert pool.free_only_mode is False
    selection = pool.acquire()
    assert selection is not None
    assert selection.key_id == "paid"
