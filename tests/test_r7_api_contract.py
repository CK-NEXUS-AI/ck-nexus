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


def test_cloud_provider_is_not_preferred_by_default_in_zero_cost_mode(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-r7-openai")
    settings = make_settings(tmp_path, mock_ai=False, ollama_enabled=False)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/providers/status")
        assert response.status_code == 200
        assert response.json()["preferred"] is None
        assert response.json()["policy"]["allow_cloud"] is False
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


def test_gmail_oauth_callback_redirects_back_to_dashboard_without_tokens(
    tmp_path: Path, monkeypatch
) -> None:
    import creator_app.gmail_oauth as gmail_module

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return (
                b'{"access_token":"gmail-access-secret",'
                b'"refresh_token":"gmail-refresh-secret","expires_in":3600}'
            )

    monkeypatch.setenv("GMAIL_CLIENT_ID", "gmail-client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "gmail-client-secret")
    monkeypatch.setattr(
        gmail_module,
        "open_trusted_request",
        lambda request, trusted_hosts, timeout: FakeResponse(),
    )
    settings = make_settings(
        tmp_path,
        gmail_oauth_enabled=True,
        gmail_redirect_uri="http://localhost:8000/api/integrations/gmail/oauth/callback",
    )
    with TestClient(create_app(settings)) as client:
        start = client.get("/api/integrations/gmail/oauth/start")
        assert start.status_code == 200
        state = parse_qs(urlparse(start.json()["authorization_url"]).query)["state"][0]
        response = client.get(
            "/api/integrations/gmail/oauth/callback",
            params={"code": "one-time-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/demo?gmail=connected"
    assert "gmail-access-secret" not in response.text
    assert "gmail-refresh-secret" not in response.text


def test_gmail_readonly_test_route_returns_only_safe_verification(
    tmp_path: Path, monkeypatch
) -> None:
    from creator_app.gmail_oauth import GmailOAuthManager

    monkeypatch.setattr(
        GmailOAuthManager,
        "verify_readonly",
        lambda self: {"connected": True, "read_only_verified": True},
    )
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.get("/api/integrations/gmail/test")

    assert response.status_code == 200
    assert response.json() == {"connected": True, "read_only_verified": True}
    assert "access_token" not in response.text
    assert "emailAddress" not in response.text


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
