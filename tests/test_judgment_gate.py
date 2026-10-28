from creator_app.n8n_intelligence.judgment_gate import JudgmentGate


def test_verified_tests_passed_allows_pr_only():
    result = JudgmentGate().evaluate("verified", True, ["creator_app/example.py"])
    assert (result.action, result.trace_level) == ("allow", 1)


def test_critical_paths_are_denied():
    for path in (
        "/etc/systemd/system/n8n.service",
        "creator_app/api_key/store.py",
        "secrets/token.json",
    ):
        result = JudgmentGate().evaluate("verified", True, [path])
        assert result.action == "deny"
        assert result.trace_level == 5


def test_auth_failure_escalates_even_when_task_is_verified():
    result = JudgmentGate().evaluate(
        "verified", False, ["creator_app/example.py"], "authentication_failure"
    )
    assert result.action == "escalate"
    assert result.trace_level == 3


def test_failed_tests_never_allow_publish():
    result = JudgmentGate().evaluate("verified", False, ["creator_app/example.py"])
    assert result.action == "edit"
    assert result.trace_level == 2


def test_unknown_state_denied():
    assert JudgmentGate().evaluate("unknown", True, []).action == "deny"
