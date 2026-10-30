from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.github_identity import GitHubIdentityError, GitHubIdentityManager


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def read(self, _size: int = -1) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def make_manager(**overrides) -> GitHubIdentityManager:
    values = {
        "client_id": "github-client-id",
        "client_secret": "github-client-secret",
        "redirect_uri": "https://example.test/api/identity/github/callback",
        "enabled": True,
    }
    values.update(overrides)
    return GitHubIdentityManager(**values)


def test_github_authorization_url_uses_read_only_identity_scope() -> None:
    manager = make_manager()
    url = manager.authorization_url()
    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == ["github-client-id"]
    assert query["scope"] == ["read:user user:email"]
    assert query["redirect_uri"] == ["https://example.test/api/identity/github/callback"]
    assert query["state"][0]
    assert "github-client-secret" not in url
    assert "repo" not in query["scope"][0]


def test_github_state_is_single_use_and_session_revoke_works(monkeypatch) -> None:
    import creator_app.github_identity as module

    manager = make_manager()
    url = manager.authorization_url()
    state = parse_qs(urlparse(url).query)["state"][0]
    bodies = iter(
        [
            b'{"access_token":"gho-private-token"}',
            b'{"login":"test-owner","id":42,"avatar_url":"https://avatars.example.test/42"}',
        ]
    )
    monkeypatch.setattr(
        module,
        "open_trusted_request",
        lambda *_args, **_kwargs: FakeResponse(next(bodies)),
    )
    session_id, identity = manager.exchange_and_verify(code="one-time-code", state=state)
    assert identity.login == "test-owner"
    assert identity.user_id == 42
    assert manager.status(session_id)["verified"] is True
    assert "gho-private-token" not in repr(manager.status(session_id))
    manager.revoke_session(session_id)
    assert manager.status(session_id)["verified"] is False
    with pytest.raises(GitHubIdentityError, match="invalid, expired, or already used"):
        manager.exchange_and_verify(code="another-code", state=state)


def test_github_identity_rejects_missing_https_configuration() -> None:
    manager = make_manager(redirect_uri="http://localhost/callback")
    assert manager.configured is False
    with pytest.raises(GitHubIdentityError, match="not fully configured"):
        manager.authorization_url()


def test_identity_portal_status_and_unconfigured_start(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("CKNEXUS_GITHUB_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("CKNEXUS_GITHUB_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("CKNEXUS_GITHUB_OAUTH_REDIRECT_URI", raising=False)
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_ENABLED", "false")
    settings = Settings(database_path=tmp_path / "identity.db", mock_ai=True, access_token="")
    with TestClient(create_app(settings)) as client:
        page = client.get("/identity")
        assert page.status_code == 200
        assert "ยืนยันตัวตนด้วย GitHub" in page.text
        status = client.get("/api/identity/github/status")
        assert status.status_code == 200
        assert status.json()["configured"] is False
        assert status.json()["verified"] is False
        assert status.json()["credential_material_exposed"] is False
        start = client.get("/api/identity/github/start", follow_redirects=False)
        assert start.status_code == 303
        assert start.headers["location"] == "/identity?result=not-configured"


def test_identity_callback_rejects_missing_state_cookie(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_ENABLED", "true")
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv(
        "CKNEXUS_GITHUB_OAUTH_REDIRECT_URI",
        "https://example.test/api/identity/github/callback",
    )
    settings = Settings(
        database_path=tmp_path / "identity-callback.db",
        mock_ai=True,
        access_token="",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/api/identity/github/callback?code=arbitrary&state=attacker-state",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/identity?result=failed"
        assert "cknexus_github_identity" not in response.headers.get("set-cookie", "")


def test_github_oauth_callback_sets_only_short_lived_identity_session(tmp_path, monkeypatch) -> None:
    import creator_app.github_identity as module

    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_ENABLED", "true")
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CKNEXUS_GITHUB_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "CKNEXUS_GITHUB_OAUTH_REDIRECT_URI",
        "https://example.test/api/identity/github/callback",
    )
    bodies = iter(
        [
            b'{"access_token":"gho-never-return-this"}',
            b'{"login":"owner-verified","id":987,"avatar_url":"https://avatars.example.test/987"}',
        ]
    )
    monkeypatch.setattr(
        module,
        "open_trusted_request",
        lambda *_args, **_kwargs: FakeResponse(next(bodies)),
    )
    settings = Settings(
        database_path=tmp_path / "identity-success.db",
        mock_ai=True,
        access_token="",
    )
    with TestClient(create_app(settings), base_url="https://example.test") as client:
        start = client.get("/api/identity/github/start", follow_redirects=False)
        assert start.status_code == 302
        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        assert "gho-never-return-this" not in start.text
        callback = client.get(
            "/api/identity/github/callback",
            params={"code": "one-time-code", "state": state},
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "/identity?result=verified"
        assert "gho-never-return-this" not in callback.text
        status = client.get("/api/identity/github/status")
        assert status.status_code == 200
        assert status.json()["verified"] is True
        assert status.json()["identity"]["login"] == "owner-verified"
        assert "gho-never-return-this" not in status.text
