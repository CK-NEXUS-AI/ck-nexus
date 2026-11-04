from __future__ import annotations

import json

import pytest

from creator_app.cloud_workers.github_actions import (
    CloudWorkerError,
    GitHubActionsCloudWorker,
)
from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.github_app import GitHubAppAuth


class FakeResponse:
    def __init__(self, body: bytes = b"", status: int = 204):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.body


def _worker(*, enabled: bool = True):
    broker = CredentialBroker(
        environment={CredentialId.GITHUB_INSTALLATION_TOKEN: "ghs-test-cloud-secret"}
    )
    auth = GitHubAppAuth(broker, enabled=True)
    return GitHubActionsCloudWorker(
        broker=broker,
        github_app_auth=auth,
        enabled=enabled,
    )


def test_status_is_read_only_and_reports_disabled_by_default():
    worker = _worker(enabled=False)
    result = worker.status()
    assert result["enabled"] is False
    assert result["configured"] is True
    assert result["arbitrary_shell_allowed"] is False
    assert result["repository_write_permission_requested"] is False
    assert result["external_mutation_authorized"] is False
    assert "ghs-test-cloud-secret" not in repr(result)


def test_dispatch_rejects_when_disabled_before_any_network_call(monkeypatch):
    import creator_app.cloud_workers.github_actions as module

    def unexpected(*_args, **_kwargs):
        raise AssertionError("network call must not happen")

    monkeypatch.setattr(module, "open_trusted_request", unexpected)
    with pytest.raises(CloudWorkerError, match="disabled"):
        _worker(enabled=False).dispatch(task_kind="tests", subject_sha="a" * 40)


@pytest.mark.parametrize(
    ("task_kind", "subject_sha"),
    [
        ("shell", "a" * 40),
        ("tests", "not-a-sha"),
        ("full_validation", "A" * 40),
        ("", "a" * 40),
    ],
)
def test_dispatch_rejects_unbounded_task_inputs(task_kind, subject_sha):
    with pytest.raises(ValueError):
        _worker().dispatch(task_kind=task_kind, subject_sha=subject_sha)


def test_dispatch_uses_fixed_workflow_and_only_allowlisted_inputs(monkeypatch):
    import creator_app.cloud_workers.github_actions as module

    captured = {}

    def fake_request(request, *, trusted_hosts, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["trusted_hosts"] = trusted_hosts
        captured["timeout"] = timeout
        return FakeResponse(status=204)

    monkeypatch.setattr(module, "open_trusted_request", fake_request)
    result = _worker().dispatch(task_kind="full_validation", subject_sha="a" * 40)

    assert result["ok"] is True
    assert result["state"] == "submitted"
    assert result["subject_sha"] == "a" * 40
    assert result["execution_location"] == "github_hosted_runner"
    assert result["external_mutation_authorized"] is False
    assert result["release_evidence"] is False
    assert captured["url"] == (
        "https://api.github.com/repos/CK-NEXUS-AI/ck-nexus/"
        "actions/workflows/cknexus-cloud-worker.yml/dispatches"
    )
    assert captured["method"] == "POST"
    assert captured["trusted_hosts"] == {"api.github.com"}
    assert captured["body"]["ref"] == "main"
    assert set(captured["body"]["inputs"]) == {
        "request_id",
        "task_kind",
        "subject_sha",
    }
    assert captured["body"]["inputs"]["task_kind"] == "full_validation"
    assert len(captured["body"]["inputs"]["request_id"]) == 32
    assert captured["headers"]["Authorization"] == "Bearer ghs-test-cloud-secret"
    assert "ghs-test-cloud-secret" not in repr(result)


def test_status_matches_exact_correlation_id_and_redacts_token(monkeypatch):
    import creator_app.cloud_workers.github_actions as module

    worker = _worker()
    request_id = "b" * 32
    response = {
        "workflow_runs": [
            {
                "display_title": "CK-NEXUS Cloud Worker " + "c" * 32,
                "id": 1,
                "status": "completed",
                "conclusion": "success",
            },
            {
                "display_title": "CK-NEXUS Cloud Worker " + request_id,
                "id": 987,
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/987",
                "head_sha": "d" * 40,
                "created_at": "2026-11-01T00:00:00Z",
                "updated_at": "2026-11-01T00:01:00Z",
            },
        ]
    }

    def fake_request(request, *, trusted_hosts, timeout):
        assert request.get_method() == "GET"
        assert "event=workflow_dispatch" in request.full_url
        assert trusted_hosts == {"api.github.com"}
        return FakeResponse(json.dumps(response).encode(), status=200)

    monkeypatch.setattr(module, "open_trusted_request", fake_request)
    result = worker.get_result(request_id=request_id)
    assert result["state"] == "completed"
    assert result["conclusion"] == "success"
    assert result["run_id"] == 987
    assert result["evidence_available"] is True
    assert result["release_evidence"] is False
    assert result["production_status"] == "NO-GO"
    assert "ghs-test-cloud-secret" not in repr(result)


def test_status_rejects_invalid_correlation_id():
    with pytest.raises(ValueError):
        _worker().get_result(request_id="../other")


def test_github_workflow_is_fixed_and_repository_is_validated():
    broker = CredentialBroker()
    auth = GitHubAppAuth(broker, enabled=False)
    with pytest.raises(ValueError, match="fixed"):
        GitHubActionsCloudWorker(
            broker=broker,
            github_app_auth=auth,
            workflow_file="arbitrary.yml",
        )
    with pytest.raises(ValueError, match="owner/name"):
        GitHubActionsCloudWorker(
            broker=broker,
            github_app_auth=auth,
            repository="../attacker",
        )
