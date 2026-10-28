import pytest

from creator_app.n8n_intelligence.circuit_breaker import CircuitOpenError, PersistentCircuitBreaker


def test_auth_failure_opens_persistent_circuit(tmp_path):
    now = [1000.0]
    breaker = PersistentCircuitBreaker(
        tmp_path / "state.json", auth_cooldown_seconds=60, clock=lambda: now[0]
    )
    breaker.record_failure(kind="auth")
    assert breaker.snapshot()["status"] == "open"
    with pytest.raises(CircuitOpenError):
        breaker.before_request()
    now[0] += 61
    breaker.before_request()
    assert breaker.snapshot()["status"] == "half_open"
    breaker.record_success()
    assert breaker.snapshot()["status"] == "closed"


def test_transient_failures_open_at_threshold(tmp_path):
    now = [1000.0]
    breaker = PersistentCircuitBreaker(
        tmp_path / "state.json",
        failure_threshold=2,
        transient_cooldown_seconds=30,
        clock=lambda: now[0],
    )
    breaker.record_failure(kind="transient")
    assert breaker.snapshot()["status"] == "closed"
    breaker.record_failure(kind="transient")
    assert breaker.snapshot()["status"] == "open"


def test_success_resets_transient_failure_budget(tmp_path):
    breaker = PersistentCircuitBreaker(tmp_path / "state.json", failure_threshold=2)
    breaker.record_failure(kind="transient")
    breaker.record_success()
    assert breaker.snapshot()["failure_count"] == 0
    assert breaker.snapshot()["status"] == "closed"


def test_state_file_permissions_are_private(tmp_path):
    breaker = PersistentCircuitBreaker(tmp_path / "state.json")
    breaker.record_failure(kind="auth")
    assert (tmp_path / "state.json").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "state.json.lock").stat().st_mode & 0o777 == 0o600
