from datetime import datetime, timedelta, timezone

import pytest

from creator_app.agnes.runtime import (
    CompensationState,
    DurableControlPlane,
    SignalState,
    TimerState,
)


def test_signal_delivery_is_idempotent_and_mismatch_fails() -> None:
    controls = DurableControlPlane()
    first = controls.deliver_signal("sig-1", "resume", {"step": 2})
    replay = controls.deliver_signal("sig-1", "resume", {"step": 2})
    assert first is replay
    assert first.state is SignalState.PENDING
    with pytest.raises(ValueError):
        controls.deliver_signal("sig-1", "resume", {"step": 3})


def test_signal_consumption_is_exactly_once() -> None:
    controls = DurableControlPlane()
    controls.deliver_signal("sig-1", "approve", {"ok": True})
    consumed = controls.consume_signal("sig-1")
    assert consumed.state is SignalState.CONSUMED
    with pytest.raises(ValueError):
        controls.consume_signal("sig-1")


def test_timer_requires_explicit_clock_and_fires_once() -> None:
    controls = DurableControlPlane()
    due = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    timer = controls.schedule_timer("timer-1", due)
    assert timer.state is TimerState.SCHEDULED
    assert controls.fire_due_timers(due - timedelta(seconds=1)) == ()
    assert controls.fire_due_timers(due) == ("timer-1",)
    assert timer.state is TimerState.FIRED
    assert controls.fire_due_timers(due + timedelta(seconds=1)) == ()


def test_timer_replay_with_changed_due_at_is_rejected() -> None:
    controls = DurableControlPlane()
    due = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    controls.schedule_timer("timer-1", due)
    with pytest.raises(ValueError):
        controls.schedule_timer("timer-1", due + timedelta(minutes=1))


def test_compensation_plan_is_reverse_order_and_explicitly_acknowledged() -> None:
    controls = DurableControlPlane()
    first = controls.register_compensation("a1", "digest-1", "undo_first")
    second = controls.register_compensation("a2", "digest-2", "undo_second")
    plan = controls.compensation_plan()
    assert [record.action_id for record in plan] == ["a2", "a1"]
    assert first.state is CompensationState.REGISTERED
    assert second.state is CompensationState.REGISTERED

    controls.mark_compensated("a2")
    assert second.state is CompensationState.COMPENSATED
    assert [record.action_id for record in controls.compensation_plan()] == ["a1"]
    with pytest.raises(ValueError):
        controls.mark_compensated("a2")


def test_compensation_replay_mismatch_is_rejected() -> None:
    controls = DurableControlPlane()
    controls.register_compensation("a1", "digest-1", "undo")
    with pytest.raises(ValueError):
        controls.register_compensation("a1", "different", "undo")
