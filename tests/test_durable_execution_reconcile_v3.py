from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from creator_app.agnes.runtime import (
    DurableCheckpoint,
    DurableControlPlane,
    DurableRun,
    DurableRunState,
    JsonFileCheckpointStore,
)


def test_checkpoint_is_deterministic_and_tamper_evident() -> None:
    left = DurableCheckpoint.create("run-1", 1, {"b": 2, "a": 1})
    right = DurableCheckpoint.create("run-1", 1, {"a": 1, "b": 2})
    assert left.digest == right.digest
    left.state["a"] = 9
    assert left.verify() is False


def test_checkpoint_rejects_invalid_parent_digest() -> None:
    with pytest.raises(ValueError, match="parent_digest"):
        DurableCheckpoint.create("run-1", 1, {}, parent_digest="not-a-digest")


def test_fork_rejects_checkpoint_from_another_run() -> None:
    source = DurableRun("source")
    source.start()
    source_checkpoint = source.advance({"value": 1})

    other = DurableRun("other")
    other.start()
    with pytest.raises(ValueError, match="another run"):
        other.fork("forked", source_checkpoint)


def test_fork_lineage_requires_exact_origin_digest() -> None:
    parent = DurableRun("parent")
    parent.start()
    parent_checkpoint = parent.advance({"value": 1})

    child = parent.fork("child", parent_checkpoint)
    child.start()
    child_checkpoint = child.advance({"value": 2})

    assert DurableRun.verify_lineage(
        [child_checkpoint],
        expected_origin_digest=parent_checkpoint.digest,
    )
    wrong_origin = "0" * 64
    assert not DurableRun.verify_lineage(
        [child_checkpoint],
        expected_origin_digest=wrong_origin,
    )


def test_restore_rejects_cross_run_checkpoint() -> None:
    first = DurableRun("first")
    first.start()
    checkpoint = first.advance({"value": 1})

    second = DurableRun("second")
    with pytest.raises(ValueError, match="another run"):
        second.restore(checkpoint)


def test_pending_writes_block_completion_until_cleared() -> None:
    run = DurableRun("write-run")
    run.start()
    run.stage_write("external-action", {"id": 1})
    with pytest.raises(ValueError, match="uncommitted pending writes"):
        run.complete()
    run.clear_pending_writes()
    run.complete()
    assert run.state is DurableRunState.COMPLETED


def test_signal_delivery_is_idempotent_and_conflicts_fail_closed() -> None:
    controls = DurableControlPlane()
    first = controls.deliver_signal("sig-1", "resume", {"step": 2})
    repeated = controls.deliver_signal("sig-1", "resume", {"step": 2})
    assert first is repeated
    with pytest.raises(ValueError, match="different content"):
        controls.deliver_signal("sig-1", "resume", {"step": 3})


def test_timer_fires_only_when_explicit_clock_is_due() -> None:
    controls = DurableControlPlane()
    due = datetime(2026, 8, 27, 4, 0, tzinfo=timezone.utc)
    controls.schedule_timer("timer-1", due)
    assert controls.fire_due_timers(due - timedelta(seconds=1)) == ()
    assert controls.fire_due_timers(due) == ("timer-1",)
    assert controls.fire_due_timers(due + timedelta(seconds=1)) == ()


def test_compensation_plan_is_reverse_order_and_replay_safe() -> None:
    controls = DurableControlPlane()
    controls.register_compensation("a1", "digest-1", "undo-a1")
    controls.register_compensation("a2", "digest-2", "undo-a2")
    assert [item.action_id for item in controls.compensation_plan()] == ["a2", "a1"]
    with pytest.raises(ValueError, match="replay mismatch"):
        controls.register_compensation("a1", "different", "undo-a1")


def test_checkpoint_store_round_trip_and_path_is_confined(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    checkpoint = DurableCheckpoint.create("../../escape", 1, {"safe": True})
    store.save(checkpoint)
    restored = store.load("../../escape")
    assert restored == checkpoint
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].parent == tmp_path


def test_checkpoint_store_rejects_tampered_file(tmp_path) -> None:
    store = JsonFileCheckpointStore(tmp_path)
    checkpoint = DurableCheckpoint.create("run-tamper", 1, {"safe": True})
    store.save(checkpoint)
    path = next(tmp_path.iterdir())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["safe"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        store.load("run-tamper")


def test_lineage_rejects_run_switch_and_step_regression() -> None:
    first = DurableCheckpoint.create("run-1", 2, {"step": 2})
    switched = DurableCheckpoint.create(
        "run-2",
        3,
        {"step": 3},
        parent_digest=first.digest,
    )
    assert not DurableRun.verify_lineage([first, switched])

    regressed = DurableCheckpoint.create(
        "run-1",
        1,
        {"step": 1},
        parent_digest=first.digest,
    )
    assert not DurableRun.verify_lineage([first, regressed])


def test_modified_digest_is_rejected_even_when_payload_is_unchanged() -> None:
    checkpoint = DurableCheckpoint.create("run-1", 1, {"value": 1})
    forged = replace(checkpoint, digest="f" * 64)
    assert forged.verify() is False
