import pytest

from creator_app.agnes.runtime import NoProgressGuard, ProgressDecision, ProgressSample


def sample(step: int, value: int, action: str) -> ProgressSample:
    return ProgressSample.create(step, {"value": value}, {"action": action})


def test_no_progress_guard_warns_then_breaks_on_identical_cycles() -> None:
    guard = NoProgressGuard(warn_after=2, break_after=3)
    first = sample(1, 1, "retry")
    second = sample(2, 1, "retry")
    third = sample(3, 1, "retry")
    assert guard.observe(first) is ProgressDecision.CONTINUE
    assert guard.observe(second) is ProgressDecision.WARN
    assert guard.observe(third) is ProgressDecision.CIRCUIT_BREAK


def test_state_progress_resets_consecutive_repeat_count() -> None:
    guard = NoProgressGuard(warn_after=2, break_after=3)
    assert guard.observe(sample(1, 1, "retry")) is ProgressDecision.CONTINUE
    assert guard.observe(sample(2, 1, "retry")) is ProgressDecision.WARN
    assert guard.observe(sample(3, 2, "retry")) is ProgressDecision.CONTINUE


def test_action_change_counts_as_progress_signal_for_guard() -> None:
    guard = NoProgressGuard(warn_after=2, break_after=3)
    assert guard.observe(sample(1, 1, "tool-a")) is ProgressDecision.CONTINUE
    assert guard.observe(sample(2, 1, "tool-b")) is ProgressDecision.CONTINUE


def test_invalid_threshold_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        NoProgressGuard(warn_after=0, break_after=3)
    with pytest.raises(ValueError):
        NoProgressGuard(warn_after=2, break_after=2)
    with pytest.raises(ValueError):
        NoProgressGuard(warn_after=2, break_after=3, history_limit=2)
