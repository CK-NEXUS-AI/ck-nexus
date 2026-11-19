from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.integrations import GoogleDriveIntegration, SlackIntegration


def test_integration_hub_is_safe_when_secrets_missing(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "hub.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/integrations/status")
        assert response.status_code == 200
        body = response.json()
        assert body["release_status"] == "release_candidate"
        ids = {item["id"] for item in body["integrations"]}
        assert {"github", "slack", "google_drive", "openai", "database"} <= ids
        assert "n8n" not in ids
        serialized = str(body).lower()
        assert "bot_token" not in serialized
        assert "api_key" not in serialized
        assert "access_token" not in serialized


def test_slack_status_reports_success(monkeypatch):
    integration = SlackIntegration("secret")
    monkeypatch.setattr(
        integration,
        "_request_json",
        lambda *args, **kwargs: {"ok": True, "team": "Aick", "user": "ck-nexus"},
    )
    status = integration.status()
    assert status.configured is True
    assert status.connected is True
    assert status.details["workspace"] == "Aick"


def test_drive_status_reports_success(monkeypatch):
    integration = GoogleDriveIntegration("secret")
    monkeypatch.setattr(
        integration,
        "_request_json",
        lambda *args, **kwargs: {"user": {"displayName": "Demo"}, "storageQuota": {"usage": "1"}},
    )
    status = integration.status()
    assert status.configured is True
    assert status.connected is True
    assert status.details["account"] == "Demo"
