import pytest

from creator_app.core.background_tasks import (
    BackgroundTask,
    BackgroundTaskController,
    BackgroundTaskState,
)
from creator_app.core.context_compaction import ContextCompactionPolicy, ContextSegment
from creator_app.core.screenshot_safety import (
    ScreenshotRisk,
    ScreenshotSafetyGate,
    ScreenshotSignal,
)


def test_screenshot_gate_blocks_without_signals() -> None:
    result = ScreenshotSafetyGate().assess(
        subject="screen:1",
        signals=[],
        policy_allows=True,
    )
    assert result.risk == ScreenshotRisk.BLOCKED
    assert result.execution_allowed is False


def test_prompt_injection_signal_never_auto_executes() -> None:
    result = ScreenshotSafetyGate().assess(
        subject="screen:2",
        signals=[
            ScreenshotSignal(
                signal_id="sig-1",
                source="prompt-injection-detector",
                confidence=0.9,
            )
        ],
        policy_allows=True,
    )
    assert result.risk == ScreenshotRisk.HIGH
    assert result.requires_human_approval is True
    assert result.execution_allowed is False


def test_background_task_requires_grant_and_checkpoint() -> None:
    controller = BackgroundTaskController()
    task = BackgroundTask(task_id="task-1", subject="subject-1")
    with pytest.raises(ValueError):
        controller.start(task)

    task.execution_grant_id = "grant-1"
    controller.start(task)
    assert task.state == BackgroundTaskState.RUNNING
    controller.suspend(task, checkpoint_id="checkpoint-1")
    assert task.state == BackgroundTaskState.SUSPENDED
    controller.resume(task)
    assert task.state == BackgroundTaskState.RUNNING


def test_context_compaction_preserves_policy_and_evidence() -> None:
    decision = ContextCompactionPolicy().plan(
        target_tokens=10,
        segments=[
            ContextSegment(
                segment_id="policy",
                token_count=8,
                importance=1.0,
                contains_policy=True,
            ),
            ContextSegment(
                segment_id="evidence",
                token_count=8,
                importance=1.0,
                contains_evidence_reference=True,
            ),
            ContextSegment(segment_id="chat", token_count=100, importance=0.1),
        ],
    )
    assert decision.policy_preserved is True
    assert decision.evidence_references_preserved is True
    assert "chat" in decision.compact_ids
