from creator_app.n8n_intelligence.models import DevelopmentSignal, N8NExecutionEvent


def test_event_validates_and_serializes():
    event = N8NExecutionEvent(
        event_id="abc123",
        execution_id="e1",
        workflow_id="w1",
        workflow_name="Build",
        status="error",
        severity="high",
        category="failure",
        message="workflow failed",
        observed_at="2026-10-24T12:00:00Z",
        metadata={"mode": "webhook"},
    )
    assert event.as_dict()["event_id"] == "abc123"
    assert event.as_dict()["metadata"] == {"mode": "webhook"}


def test_signal_has_bounded_priority():
    signal = DevelopmentSignal(
        event_id="abc123",
        execution_id="e1",
        category="bug",
        severity="high",
        title="Fix workflow failure",
        description="failure",
        priority=3,
    )
    assert signal.priority == 3
