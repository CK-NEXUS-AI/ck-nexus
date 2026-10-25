from creator_app.n8n_intelligence.analysis import (
    classify_execution,
    fingerprint_execution,
    priority_for,
    sanitize_message,
)


def test_sanitize_message_redacts_secrets_and_bounds_text():
    text = "token=super-secret password: hunter2 " + "x" * 5000
    result = sanitize_message(text)
    assert "super-secret" not in result
    assert "hunter2" not in result
    assert len(result) <= 1000


def test_fingerprint_is_stable_for_same_execution():
    execution = {"id": "e1", "workflowId": "w1", "status": "error", "stoppedAt": "t1"}
    assert fingerprint_execution(execution) == fingerprint_execution(dict(execution))


def test_success_is_not_actionable():
    assert classify_execution({"id": "e1", "status": "success", "workflowId": "w1"}, 30) is None


def test_failure_and_slow_execution_are_actionable():
    failed = classify_execution(
        {
            "id": "e1",
            "status": "error",
            "workflowId": "w1",
            "duration": 2,
            "error": {"message": "boom"},
        },
        30,
    )
    slow = classify_execution(
        {"id": "e2", "status": "success", "workflowId": "w1", "duration": 45}, 30
    )
    assert failed is not None and failed.category == "bug"
    assert slow is not None and slow.category == "performance"


def test_mixed_timezone_timestamps_do_not_crash_duration_analysis():
    execution = {
        "id": "e3",
        "status": "success",
        "workflowId": "w1",
        "startedAt": "2026-10-24T00:00:00",
        "stoppedAt": "2026-10-24T00:01:00Z",
    }
    assert classify_execution(execution, 30) is None


def test_repeat_failure_escalates_but_stays_bounded():
    assert priority_for("bug", 1) == 2
    assert priority_for("bug", 3) == 3
    assert priority_for("performance", 99) == 3
