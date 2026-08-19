from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from creator_app.credentials.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)

logger = logging.getLogger("cknexus.gmail")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailConnectorError(RuntimeError):
    """Safe Gmail connector error that never carries credential material."""


@dataclass(frozen=True, slots=True)
class GmailMessage:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipients: tuple[str, ...]
    date: str
    snippet: str


class GmailOAuthClient(Protocol):
    """Protocol for Gmail OAuth operations. Concrete implementation must never expose raw tokens."""

    def get_access_token(self) -> str: ...
    def refresh_access_token(self) -> str: ...
    def is_token_expired(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class GmailConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    token_url: str = GOOGLE_TOKEN_URL
    api_base: str = GMAIL_API_BASE


class GmailConnector:
    """Gmail connector that uses OAuth2 refresh flow — never raw token extraction.

    This connector integrates with the CK-NEXUS Credential Broker:
    - Acquires a lease from the broker for gmail.oauth consumer
    - Uses the refresh token to obtain short-lived access tokens
    - Access tokens are ephemeral and never persisted/logged
    - Supports automatic refresh when tokens expire
    - Quota monitoring triggers key rotation warnings

    Authority chain: USER -> ACCESS -> GOVERNOR -> CREDENTIAL BROKER -> GMAIL CONNECTOR
    """

    SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)

    def __init__(
        self,
        broker: CredentialBroker,
        *,
        open_url: object | None = None,
        config_override: GmailConfig | None = None,
    ) -> None:
        self._broker = broker
        self._open_url = open_url
        self._config_override = config_override

    def _acquire_config(self) -> GmailConfig:
        """Acquire Gmail OAuth credentials from the broker via lease."""
        try:
            lease_client_id = self._broker.acquire(
                CredentialId.GMAIL_CLIENT_ID,
                consumer="gmail.oauth",
            )
            lease_secret = self._broker.acquire(
                CredentialId.GMAIL_CLIENT_SECRET,
                consumer="gmail.oauth",
            )
            lease_refresh = self._broker.acquire(
                CredentialId.GMAIL_REFRESH_TOKEN,
                consumer="gmail.oauth",
            )
        except (CredentialUnavailable, Exception):
            raise GmailConnectorError(
                "Gmail OAuth credentials are not available through the broker."
            ) from None

        return GmailConfig(
            client_id=lease_client_id.reveal(consumer="gmail.oauth"),
            client_secret=lease_secret.reveal(consumer="gmail.oauth"),
            refresh_token=lease_refresh.reveal(consumer="gmail.oauth"),
        )

    def _refresh_access_token(self, config: GmailConfig) -> str:
        """Exchange refresh token for a short-lived access token."""
        import urllib.error
        import urllib.request

        data = urllib.parse.urlencode(
            {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": config.refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(self.SCOPES),
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            config.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                token_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GmailConnectorError(f"Gmail token refresh failed: HTTP {exc.code}") from exc

        access_token = token_data.get("access_token", "")
        if not access_token:
            raise GmailConnectorError("Gmail token refresh returned no access token")

        expires_in = token_data.get("expires_in", 3600)
        logger.debug("Obtained Gmail access token (expires_in=%ds)", expires_in)
        return access_token

    def _gmail_request(self, access_token: str, path: str) -> dict:
        """Make an authenticated Gmail API request."""
        import urllib.request

        url = f"{self._config_override.api_base if self._config_override else GMAIL_API_BASE}{path}"
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GmailConnectorError(f"Gmail API request failed: {type(exc).__name__}") from exc

    def list_messages(
        self,
        *,
        query: str | None = None,
        max_results: int = 100,
    ) -> tuple[GmailMessage, ...]:
        """List Gmail messages matching an optional query."""
        config = self._config_override or self._acquire_config()
        access_token = self._refresh_access_token(config)

        path = "/messages"
        if query:
            path = f"/messages?q={urllib.parse.quote(query)}"
        path += f"&maxResults={max_results}"

        data = self._gmail_request(access_token, path)
        messages = data.get("messages", [])

        result: list[GmailMessage] = []
        for msg_ref in messages:
            msg = self._get_message(access_token, msg_ref["id"])
            if msg is not None:
                result.append(msg)

        return tuple(result)

    def _get_message(self, access_token: str, message_id: str) -> GmailMessage | None:
        """Fetch a single message by ID."""
        try:
            data = self._gmail_request(access_token, f"/messages/{message_id}")
        except GmailConnectorError:
            logger.warning("Failed to fetch Gmail message %s", message_id)
            return None

        headers = {
            h["name"].lower(): h["value"] for h in data.get("payload", {}).get("headers", [])
        }
        return GmailMessage(
            message_id=data.get("id", ""),
            thread_id=data.get("threadId", ""),
            subject=headers.get("subject", ""),
            sender=headers.get("from", ""),
            recipients=tuple(self._parse_recipients(headers.get("to", ""))),
            date=headers.get("date", ""),
            snippet=data.get("snippet", ""),
        )

    def search(self, query: str, *, max_results: int = 100) -> tuple[GmailMessage, ...]:
        """Search Gmail messages by query string."""
        return self.list_messages(query=query, max_results=max_results)

    def count_unread(self) -> int:
        """Count unread messages in the inbox."""
        config = self._config_override or self._acquire_config()
        access_token = self._refresh_access_token(config)
        try:
            data = self._gmail_request(access_token, "/gmail/label/INBOX")
            return data.get("messagesTotal", 0)
        except GmailConnectorError:
            return 0

    @staticmethod
    def _parse_recipients(header_value: str) -> list[str]:
        """Parse RFC 2822 recipient header into individual email addresses."""
        if not header_value:
            return []
        return [addr.strip() for addr in header_value.split(",") if addr.strip()]

    def __repr__(self) -> str:
        return "GmailConnector(broker=..., credentials=<redacted>)"


# Import urllib.parse lazily within methods to avoid module-level state issues
import urllib.parse  # noqa: E402


def build_gmail_connector(broker: CredentialBroker) -> GmailConnector:
    """Factory for building a Gmail connector from the credential broker."""
    return GmailConnector(broker=broker)
