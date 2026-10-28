from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.github_app import GitHubAppAuth
from creator_app.gmail_oauth import GmailOAuthError, GmailOAuthManager


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_gmail_authorization_url_is_least_privilege(monkeypatch) -> None:
    broker = CredentialBroker(
        environment={
            CredentialId.GMAIL_CLIENT_ID: "client-id",
            CredentialId.GMAIL_CLIENT_SECRET: "client-secret",
        }
    )
    manager = GmailOAuthManager(
        broker,
        enabled=True,
        redirect_uri="http://localhost:8000/api/integrations/gmail/oauth/callback",
        include_send_scope=False,
    )
    url = manager.authorization_url()
    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == ["client-id"]
    assert "gmail.readonly" in query["scope"][0]
    assert "gmail.send" not in query["scope"][0]
    assert "client-secret" not in url
    assert query["access_type"] == ["offline"]


def test_gmail_state_is_one_time() -> None:
    broker = CredentialBroker(
        environment={
            CredentialId.GMAIL_CLIENT_ID: "client-id",
            CredentialId.GMAIL_CLIENT_SECRET: "client-secret",
        }
    )
    manager = GmailOAuthManager(
        broker,
        enabled=True,
        redirect_uri="http://localhost:8000/callback",
    )
    state = parse_qs(urlparse(manager.authorization_url()).query)["state"][0]
    manager.state_store.consume(state)
    with pytest.raises(GmailOAuthError, match="invalid or expired"):
        manager.state_store.consume(state)


def test_gmail_readonly_verification_checks_google_api_without_exposing_profile(
    monkeypatch,
) -> None:
    import creator_app.gmail_oauth as gmail_module

    broker = CredentialBroker(
        environment={
            CredentialId.GMAIL_CLIENT_ID: "client-id",
            CredentialId.GMAIL_CLIENT_SECRET: "client-secret",
        }
    )
    broker.put_ephemeral(
        CredentialId.GMAIL_ACCESS_TOKEN,
        "gmail-access-secret",
        source="gmail-oauth-test",
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b'{"emailAddress":"private@example.com","messagesTotal":42}'

    captured = {}
    def fake_request(request, trusted_hosts, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["hosts"] = trusted_hosts
        return FakeResponse()

    monkeypatch.setattr(gmail_module, "open_trusted_request", fake_request)
    manager = GmailOAuthManager(
        broker,
        enabled=True,
        redirect_uri="http://localhost:8000/callback",
    )

    result = manager.verify_readonly()

    assert result == {"connected": True, "read_only_verified": True}
    assert captured["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/profile"
    assert captured["hosts"] == {"gmail.googleapis.com"}
    assert captured["authorization"] == "Bearer gmail-access-secret"
    assert "private@example.com" not in repr(result)
    assert "gmail-access-secret" not in repr(result)


def test_gmail_readonly_verification_refreshes_expired_access_token(monkeypatch) -> None:
    import creator_app.gmail_oauth as gmail_module

    broker = CredentialBroker(
        environment={
            CredentialId.GMAIL_CLIENT_ID: "client-id",
            CredentialId.GMAIL_CLIENT_SECRET: "client-secret",
        }
    )
    broker.put_ephemeral(
        CredentialId.GMAIL_REFRESH_TOKEN,
        "gmail-refresh-secret",
        source="gmail-oauth-test",
    )

    class FakeResponse:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return self.body

    calls = []
    def fake_request(request, trusted_hosts, timeout):
        calls.append((request.full_url, trusted_hosts))
        if request.full_url == "https://oauth2.googleapis.com/token":
            return FakeResponse(b'{"access_token":"new-access-secret","expires_in":3600}')
        return FakeResponse(b'{"emailAddress":"private@example.com","messagesTotal":42}')

    monkeypatch.setattr(gmail_module, "open_trusted_request", fake_request)
    manager = GmailOAuthManager(
        broker,
        enabled=True,
        redirect_uri="http://localhost:8000/callback",
    )

    result = manager.verify_readonly()

    assert result == {"connected": True, "read_only_verified": True}
    assert calls == [
        ("https://oauth2.googleapis.com/token", {"oauth2.googleapis.com"}),
        ("https://gmail.googleapis.com/gmail/v1/users/me/profile", {"gmail.googleapis.com"}),
    ]
    refreshed = broker.acquire(CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api")
    assert refreshed.reveal(consumer="gmail.api") == "new-access-secret"
    assert "gmail-refresh-secret" not in repr(result)
    assert "new-access-secret" not in repr(result)


def test_github_app_status_never_returns_token() -> None:
    broker = CredentialBroker(
        environment={
            CredentialId.GITHUB_APP_ID: "123",
            CredentialId.GITHUB_APP_PRIVATE_KEY: "PRIVATE-KEY-MATERIAL",
            CredentialId.GITHUB_APP_INSTALLATION_ID: "456",
        }
    )
    auth = GitHubAppAuth(
        broker,
        enabled=True,
        jwt_signer=lambda payload, key: "jwt-redacted-test",
    )
    status = auth.status()
    assert status["configured"] is True
    text = repr(status)
    assert "PRIVATE-KEY-MATERIAL" not in text
    assert "jwt-redacted-test" not in text


def test_gmail_exchange_stores_tokens_only_in_broker(monkeypatch) -> None:
    import creator_app.gmail_oauth as gmail_module

    broker = CredentialBroker(
        environment={
            CredentialId.GMAIL_CLIENT_ID: "client-id",
            CredentialId.GMAIL_CLIENT_SECRET: "client-secret",
        }
    )
    manager = GmailOAuthManager(
        broker,
        enabled=True,
        redirect_uri="http://localhost:8000/callback",
    )
    state = parse_qs(urlparse(manager.authorization_url()).query)["state"][0]

    body = (
        b'{"access_token":"gmail-access-secret",'
        b'"refresh_token":"gmail-refresh-secret","expires_in":3600}'
    )
    monkeypatch.setattr(
        gmail_module,
        "open_trusted_request",
        lambda request, trusted_hosts, timeout: FakeResponse(body),
    )
    status = manager.exchange_code(code="one-time-code", state=state)

    assert status["authorized"] is True
    assert "gmail-access-secret" not in repr(status)
    assert "gmail-refresh-secret" not in repr(status)
    access = broker.acquire(CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api")
    refresh = broker.acquire(CredentialId.GMAIL_REFRESH_TOKEN, consumer="gmail.api")
    assert access.reveal(consumer="gmail.api") == "gmail-access-secret"
    assert refresh.reveal(consumer="gmail.api") == "gmail-refresh-secret"


def test_github_app_mints_short_lived_token_without_returning_it(monkeypatch) -> None:
    import creator_app.github_app as github_module

    broker = CredentialBroker(
        environment={
            CredentialId.GITHUB_APP_ID: "123",
            CredentialId.GITHUB_APP_PRIVATE_KEY: "PRIVATE-KEY-MATERIAL",
            CredentialId.GITHUB_APP_INSTALLATION_ID: "456",
        }
    )
    captured = {}

    def signer(payload, key):
        captured["payload"] = payload
        captured["key"] = key
        return "jwt-secret"

    body = b'{"token":"ghs-installation-secret","expires_at":"2099-01-01T00:00:00Z"}'
    monkeypatch.setattr(
        github_module,
        "open_trusted_request",
        lambda request, trusted_hosts, timeout: FakeResponse(body),
    )
    auth = GitHubAppAuth(broker, enabled=True, jwt_signer=signer)
    status = auth.ensure_installation_token()

    assert status["installation_token_ready"] is True
    assert "ghs-installation-secret" not in repr(status)
    assert captured["key"] == "PRIVATE-KEY-MATERIAL"
    assert int(captured["payload"]["exp"]) - int(captured["payload"]["iat"]) <= 600
    lease = broker.acquire(CredentialId.GITHUB_INSTALLATION_TOKEN, consumer="github.app")
    assert lease.reveal(consumer="github.app") == "ghs-installation-secret"
