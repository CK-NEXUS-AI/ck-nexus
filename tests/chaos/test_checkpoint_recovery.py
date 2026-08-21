from pathlib import Path

import pytest

from creator_app.core.durable_persistence import JsonlDurableStore
from creator_app.core.durable_runtime import Checkpoint, DurableTask, DurableTaskState


@pytest.mark.chaos
def test_checkpoint_recovery_after_process_recreation(
    tmp_path: Path,
    ck_chaos_level: int,
) -> None:
    if ck_chaos_level < 1:
        pytest.skip("requires --chaos-level>=1")

    state_path = tmp_path / "state.jsonl"
    before_crash = JsonlDurableStore(state_path)
    checkpoint = Checkpoint(
        checkpoint_id="cp:5",
        subject="task:chaos",
        state_digest="sha256:step-5",
    )
    task = DurableTask(
        task_id="task:chaos",
        subject="task:chaos",
        state=DurableTaskState.SUSPENDED,
        checkpoint_ids=[checkpoint.checkpoint_id],
        resume_token_ref="credential-ref:resume:chaos",
    )
    before_crash.append_checkpoint(checkpoint)
    before_crash.append_task(task)

    after_restart = JsonlDurableStore(state_path)
    records = after_restart.read_all()

    assert [record.record_type for record in records] == ["checkpoint", "task"]
    assert records[0].payload["state_digest"] == "sha256:step-5"
    assert records[1].payload["resume_token_ref"] == "credential-ref:resume:chaos"
