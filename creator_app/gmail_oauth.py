from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlencode
from urllib.request import Request

from creator_app.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)
from creator_app.integration_security import open_trusted_request

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailOAuthError(RuntimeError):
    """Safe OAuth error that never contains authorization codes or tokens."""


@dataclass(slots=True)
class _OAuthState:
    expires_at: float


class OAuthStateStore:
    def __init__(self, *, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._states: dict[str, _OAuthState] = {}

    def issue(self) -> str:
        state = secrets.token_urlsafe(32)
        self._states[state] = _OAuthState(monotonic() + self.ttl_seconds)
        return state

    def consume(self, state: str) -> None:
        record = self._states.pop(state, None)
        if record is None or monotonic() >= record.expires_at:
            raise GmailOAuthError("OAuth state is invalid or expired.")


class GmailOAuthManager:
    def __init__(
        self,
        broker: CredentialBroker,
        *,
        enabled: bool,
        redirect_uri: str,
        include_send_scope: bool = False,
        timeout_seconds: int = 10,
        state_store: OAuthStateStore | None = None,
    ) -> None:
        self.broker = broker
        self.enabled = enabled
        self.redirect_uri = redirect_uri.strip()
        self.include_send_scope = include_send_scope
        self.timeout_seconds = timeout_seconds
        self.state_store = state_store or OAuthStateStore()

    @property
    def scopes(self) -> tuple[str, ...]:
        scopes = [GMAIL_READONLY_SCOPE]
        if self.include_send_scope:
            scopes.append(GMAIL_SEND_SCOPE)
        return tuple(scopes)

    @property
    def configured(self) -> bool:
        return (
            self.enabled
            and bool(self.redirect_uri)
            and self.broker.is_configured(CredentialId.GMAIL_CLIENT_ID, consumer="gmail.oauth")
            and self.broker.is_configured(
                CredentialId.GMAIL_CLIENT_SECRET, consumer="gmail.oauth"
            )
        )

    @property
    def authorized(self) -> bool:
        return self.broker.is_configured(
            CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api"
        ) or self.broker.is_configured(
            CredentialId.GMAIL_REFRESH_TOKEN, consumer="gmail.api"
        )

    def status(self) -> dict[str, object]:
        return {
            "id": "gmail",
            "enabled": self.enabled,
            "configured": self.configured,
            "authorized": self.authorized,
            "scopes": list(self.scopes),
            "token_persistence": (
                "encrypted-vault" if self.broker.persistent_available else "ephemeral-memory"
            ),
            "production_vault_required": not self.broker.persistent_available,
        }

    def revoke_local_tokens(self) -> dict[str, object]:
        for credential_id in (
            CredentialId.GMAIL_ACCESS_TOKEN,
            CredentialId.GMAIL_REFRESH_TOKEN,
        ):
            self.broker.clear_ephemeral(credential_id)
            self.broker.clear_persistent(credential_id, reason="revoked")
        return self.status()

    def authorization_url(self) -> str:
        if not self.configured:
            raise GmailOAuthError("Gmail OAuth is not fully configured.")
        client_id = self.broker.acquire(
            CredentialId.GMAIL_CLIENT_ID, consumer="gmail.oauth"
        ).reveal(consumer="gmail.oauth")
        state = self.state_store.issue()
        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.scopes),
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent",
                "state": state,
            }
        )
        return f"{GOOGLE_AUTH_URL}?{query}"

    def exchange_code(self, *, code: str, state: str) -> dict[str, object]:
        if not self.configured:
            raise GmailOAuthError("Gmail OAuth is not fully configured.")
        if not code.strip():
            raise GmailOAuthError("OAuth authorization code is missing.")
        self.state_store.consume(state)
        try:
            client_id = self.broker.acquire(
                CredentialId.GMAIL_CLIENT_ID, consumer="gmail.oauth"
            ).reveal(consumer="gmail.oauth")
            client_secret = self.broker.acquire(
                CredentialId.GMAIL_CLIENT_SECRET, consumer="gmail.oauth"
            ).reveal(consumer="gmail.oauth")
        except CredentialUnavailable as exc:
            raise GmailOAuthError("Gmail OAuth client credentials are unavailable.") from exc

        payload = urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
        ).encode("utf-8")
        request = Request(
            GOOGLE_TOKEN_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts={"oauth2.googleapis.com"},
                timeout=self.timeout_seconds,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GmailOAuthError("Gmail OAuth token exchange failed safely.") from exc

        access_token = str(body.get("access_token") or "").strip()
        refresh_token = str(body.get("refresh_token") or "").strip()
        expires_in = int(body.get("expires_in") or 3600)
        if not access_token:
            raise GmailOAuthError("Gmail OAuth response did not contain an access token.")
        self.broker.put_ephemeral(
            CredentialId.GMAIL_ACCESS_TOKEN,
            access_token,
            source="gmail-oauth",
            ttl_seconds=max(60, expires_in - 30),
        )
        if refresh_token:
            if self.broker.persistent_available:
                self.broker.put_persistent(
                    CredentialId.GMAIL_REFRESH_TOKEN,
                    refresh_token,
                    source="gmail-oauth",
                )
            else:
                self.broker.put_ephemeral(
                    CredentialId.GMAIL_REFRESH_TOKEN,
                    refresh_token,
                    source="gmail-oauth",
                )
        return self.status()
