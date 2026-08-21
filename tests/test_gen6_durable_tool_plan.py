from pathlib import Path

import pytest

from creator_app.core.durable_persistence import JsonlDurableStore
from creator_app.core.durable_runtime import Checkpoint, DurableTask, DurableTaskState
from creator_app.core.programmatic_tool_plan import (
    ProgrammaticToolPlan,
    ToolPlanPolicy,
    ToolRisk,
    ToolStep,
)


def test_durable_store_rejects_raw_resume_secret(tmp_path: Path) -> None:
    store = JsonlDurableStore(tmp_path / "durable.jsonl")
    task = DurableTask(
        task_id="task-1",
        subject="subject-1",
        state=DurableTaskState.SUSPENDED,
        checkpoint_ids=["cp-1"],
        resume_token_ref="raw-secret-value",
    )
    with pytest.raises(ValueError):
        store.append_task(task)


def test_durable_store_appends_digest_only_records(tmp_path: Path) -> None:
    store = JsonlDurableStore(tmp_path / "durable.jsonl")
    checkpoint = Checkpoint(
        checkpoint_id="cp-1",
        subject="subject-1",
        state_digest="sha256:abc",
    )
    task = DurableTask(
        task_id="task-1",
        subject="subject-1",
        state=DurableTaskState.SUSPENDED,
        checkpoint_ids=["cp-1"],
        resume_token_ref="credential-ref:resume-1",
    )
    store.append_checkpoint(checkpoint)
    store.append_task(task)
    records = store.read_all()
    assert [record.record_type for record in records] == ["checkpoint", "task"]
    assert records[0].payload["state_digest"] == "sha256:abc"


def test_high_risk_tool_step_requires_approval_and_grant() -> None:
    plan = ProgrammaticToolPlan(
        plan_id="plan-1",
        subject="subject-1",
        policy_decision_id="policy-1",
        steps=[
            ToolStep(
                step_id="step-1",
                tool_name="desktop.click",
                intent="Submit a governed UI action",
                risk=ToolRisk.HIGH,
            )
        ],
    )
    assert not plan.executable
    with pytest.raises(ValueError):
        ToolPlanPolicy.validate(plan)


def test_low_risk_tool_plan_can_be_executable_with_policy() -> None:
    plan = ProgrammaticToolPlan(
        plan_id="plan-2",
        subject="subject-1",
        policy_decision_id="policy-1",
        steps=[
            ToolStep(
                step_id="step-1",
                tool_name="file.search",
                intent="Search approved workspace files",
                risk=ToolRisk.LOW,
            )
        ],
    )
    assert plan.executable
    ToolPlanPolicy.validate(plan)
