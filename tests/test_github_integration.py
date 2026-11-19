from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.github_integration import GitHubIntegration


def test_github_status_is_safe_when_token_missing(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "github-test.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/integrations/github/status")
        assert response.status_code == 200
        body = response.json()
        assert body["configured"] is False
        assert body["connected"] is False
        assert body["repository_access"] is False
        assert "token" not in str(body).lower().replace("github_token", "")


def test_github_integration_reports_authenticated_repository(monkeypatch):
    integration = GitHubIntegration("test-secret", repository="owner/repo")

    def fake_request(path: str):
        if path == "/user":
            return {"login": "demo-user"}
        if path == "/repos/owner/repo":
            return {"default_branch": "main"}
        raise AssertionError(path)

    monkeypatch.setattr(integration, "_request_json", fake_request)
    status = integration.status()
    assert status.configured is True
    assert status.connected is True
    assert status.login == "demo-user"
    assert status.repository_access is True
    assert status.default_branch == "main"
