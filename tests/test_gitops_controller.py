from creator_app.n8n_intelligence.gitops_controller import SafeGitOpsController


def test_controller_blocks_unverified_work_before_network_call():
    controller = SafeGitOpsController("fake-token", "owner/repo")
    controller._request = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("network must not run")
    )
    result = controller.create_pull_request(
        task_id="job-1",
        branch="cknexus/auto-dev/0123456789abcdef",
        commit_sha="a" * 40,
        state="verified",
        tests_ok=False,
        changed_paths=["creator_app/example.py"],
    )
    assert result.state == "blocked"
    assert result.reason.startswith("judgment_edit:")


def test_controller_rejects_untrusted_branch_before_network_call():
    controller = SafeGitOpsController("fake-token", "owner/repo")
    controller._request = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("network must not run")
    )
    result = controller.create_pull_request(
        task_id="job-1",
        branch="main",
        commit_sha="a" * 40,
        state="verified",
        tests_ok=True,
        changed_paths=["creator_app/example.py"],
    )
    assert result.state == "blocked"
    assert result.reason == "branch_or_commit_identity_invalid"


def test_controller_returns_existing_open_pr_idempotently():
    controller = SafeGitOpsController("fake-token", "owner/repo")
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        if "/git/ref/" in url:
            return {"object": {"sha": "a" * 40}}
        return [{"html_url": "https://github.com/owner/repo/pull/17", "number": 17}]

    controller._request = fake_request
    result = controller.create_pull_request(
        task_id="job-1",
        branch="cknexus/auto-dev/0123456789abcdef",
        commit_sha="a" * 40,
        state="verified",
        tests_ok=True,
        changed_paths=["creator_app/example.py"],
    )
    assert result.state == "existing"
    assert result.number == 17
    assert len(calls) == 2 and all(call[0] == "GET" for call in calls)


def test_controller_creates_draft_pr_after_gate_passes():
    controller = SafeGitOpsController("fake-token", "owner/repo")
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        if "/git/ref/" in url:
            return {"object": {"sha": "b" * 40}}
        if method == "GET":
            return []
        return {"html_url": "https://github.com/owner/repo/pull/18", "number": 18}

    controller._request = fake_request
    result = controller.create_pull_request(
        task_id="job-2",
        branch="cknexus/auto-dev/0123456789abcdef",
        commit_sha="b" * 40,
        state="verified",
        tests_ok=True,
        changed_paths=["creator_app/example.py"],
    )
    assert result.state == "created"
    assert result.number == 18
    assert calls[0][0] == "GET" and "/git/ref/" in calls[0][1]
    assert calls[1][0] == "GET" and "/pulls?" in calls[1][1]
    assert calls[2][0] == "POST"
    assert calls[2][2]["draft"] is True
    assert calls[2][2]["base"] == "main"


def test_controller_refuses_pr_if_remote_branch_sha_differs():
    controller = SafeGitOpsController("fake-token", "owner/repo")
    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        return {"object": {"sha": "c" * 40}}

    controller._request = fake_request
    result = controller.create_pull_request(
        task_id="job-3",
        branch="cknexus/auto-dev/0123456789abcdef",
        commit_sha="b" * 40,
        state="verified",
        tests_ok=True,
        changed_paths=["creator_app/example.py"],
    )
    assert result.state == "blocked"
    assert result.reason == "remote_branch_sha_mismatch"
    assert len(calls) == 1
