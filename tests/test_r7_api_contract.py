from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "r7.db",
        "mock_ai": True,
        "access_token": "",
        "rate_limit_per_minute": 50,
    }
    values.update(overrides)
    return Settings(**values)


def test_provider_and_credential_status_are_redacted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-r7-contract-secret")
    with TestClient(create_app(make_settings(tmp_path))) as client:
        providers = client.get("/api/providers/status")
        assert providers.status_code == 200
        assert providers.json()["preferred"] == "mock"

        credentials = client.get("/api/security/credentials/status")
        assert credentials.status_code == 200
        body = credentials.json()
        assert body["secrets_exposed"] is False
        assert "sk-r7-contract-secret" not in credentials.text
        openai = body["consumers"]["provider.openai"]
        assert any(item["id"] == "openai.api_key" and item["configured"] for item in openai)


def test_openai_is_preferred_when_mock_and_ollama_are_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-r7-openai")
    settings = make_settings(tmp_path, mock_ai=False, ollama_enabled=False)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/providers/status")
        assert response.status_code == 200
        assert response.json()["preferred"] == "openai"
        assert "sk-r7-openai" not in response.text


def test_gmail_oauth_start_never_exposes_client_secret(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GMAIL_CLIENT_ID", "gmail-client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "gmail-client-secret")
    settings = make_settings(
        tmp_path,
        gmail_oauth_enabled=True,
        gmail_redirect_uri="http://localhost:8000/api/integrations/gmail/oauth/callback",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/integrations/gmail/oauth/start")
        assert response.status_code == 200
        url = response.json()["authorization_url"]
        query = parse_qs(urlparse(url).query)
        assert query["client_id"] == ["gmail-client-id"]
        assert "gmail-client-secret" not in url
        assert "gmail.readonly" in query["scope"][0]


def test_github_app_status_is_redacted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "456")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "PRIVATE-KEY-R7")
    settings = make_settings(tmp_path, github_app_enabled=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/integrations/github-app/status")
        assert response.status_code == 200
        assert response.json()["configured"] is True
        assert "PRIVATE-KEY-R7" not in response.text
