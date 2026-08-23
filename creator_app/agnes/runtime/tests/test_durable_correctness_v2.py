import pytest

from creator_app.agnes.runtime.durable import DurableCheckpoint, DurableRun, DurableRunState


def test_checkpoint_digest_detects_tampering():
    run = DurableRun("run-1")
    run.start()
    checkpoint = run.advance({"x": 1})
    tampered = DurableCheckpoint(
        run_id=checkpoint.run_id,
        step_index=checkpoint.step_index,
        state={"x": 2},
        digest=checkpoint.digest,
        parent_digest=checkpoint.parent_digest,
        pending_writes=checkpoint.pending_writes,
    )
    assert tampered.verify() is False


def test_lineage_is_chained():
    run = DurableRun("run-2")
    run.start()
    first = run.advance({"a": 1})
    second = run.advance({"b": 2})
    assert first.parent_digest is None
    assert second.parent_digest == first.digest
    assert DurableRun.verify_lineage(run.checkpoints) is True


def test_restore_recovers_pending_writes_and_state():
    run = DurableRun("run-3")
    run.start()
    run.stage_write("artifact", {"id": 7})
    checkpoint = run.advance({"phase": "build"})
    run.logical_state["phase"] = "corrupt"
    run.clear_pending_writes()
    run.restore(checkpoint)
    assert run.state is DurableRunState.PAUSED
    assert run.logical_state == {"phase": "build"}
    assert run.pending_writes == {"artifact": {"id": 7}}


def test_complete_fails_closed_with_pending_writes():
    run = DurableRun("run-4")
    run.start()
    run.stage_write("external", "pending")
    with pytest.raises(ValueError, match="uncommitted pending writes"):
        run.complete()
    run.clear_pending_writes()
    run.complete()
    assert run.state is DurableRunState.COMPLETED


def test_replay_to_previous_step():
    run = DurableRun("run-5")
    run.start()
    run.advance({"n": 1})
    run.advance({"n": 2})
    replayed = run.replay_to(1)
    assert replayed.step_index == 1
    assert run.logical_state == {"n": 1}
    assert run.state is DurableRunState.PAUSED


def test_fork_preserves_origin_digest_but_gets_new_identity():
    parent = DurableRun("parent")
    parent.start()
    checkpoint = parent.advance({"value": 10})
    child = parent.fork("child", checkpoint)
    assert child.run_id == "child"
    assert child.origin_checkpoint_digest == checkpoint.digest
    assert child.logical_state == checkpoint.state
    assert child.state is DurableRunState.PAUSED


def test_cross_run_restore_is_rejected():
    source = DurableRun("source")
    source.start()
    checkpoint = source.advance({"x": 1})
    target = DurableRun("target")
    with pytest.raises(ValueError, match="another run"):
        target.restore(checkpoint)
