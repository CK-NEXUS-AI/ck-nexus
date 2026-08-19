from __future__ import annotations

import json
import logging
import urllib.error
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request

from creator_app.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)
from creator_app.integration_security import open_trusted_request

logger = logging.getLogger("cknexus.gmail")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
_GOOGLE_TOKEN_HOSTS = frozenset({"oauth2.googleapis.com"})
_GMAIL_API_HOSTS = frozenset({"gmail.googleapis.com"})


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
    """Protocol for Gmail OAuth operations that never returns tokens in status output."""

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
    """Read-only Gmail connector using brokered OAuth refresh credentials.

    Credential-bearing requests are restricted to exact Google HTTPS hosts and
    redirects are disabled by ``open_trusted_request``. Access tokens remain
    ephemeral and are never returned by status/reporting APIs.
    """

    SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)

    def __init__(
        self,
        broker: CredentialBroker,
        *,
        config_override: GmailConfig | None = None,
    ) -> None:
        self._broker = broker
        self._config_override = config_override

    def _acquire_config(self) -> GmailConfig:
        """Acquire Gmail OAuth credentials from the broker via scoped leases."""
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
        except CredentialUnavailable:
            raise GmailConnectorError(
                "Gmail OAuth credentials are not available through the broker."
            ) from None

        return GmailConfig(
            client_id=lease_client_id.reveal(consumer="gmail.oauth"),
            client_secret=lease_secret.reveal(consumer="gmail.oauth"),
            refresh_token=lease_refresh.reveal(consumer="gmail.oauth"),
        )

    def _refresh_access_token(self, config: GmailConfig) -> str:
        """Exchange a refresh token for a short-lived access token."""
        data = urlencode(
            {
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": config.refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(self.SCOPES),
            }
        ).encode("utf-8")

        request = Request(
            config.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts=_GOOGLE_TOKEN_HOSTS,
                timeout=10,
            ) as response:
                token_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GmailConnectorError(f"Gmail token refresh failed: HTTP {exc.code}") from None
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            raise GmailConnectorError(
                f"Gmail token refresh failed: {type(exc).__name__}"
            ) from None

        access_token = token_data.get("access_token", "")
        if not isinstance(access_token, str) or not access_token:
            raise GmailConnectorError("Gmail token refresh returned no access token")

        expires_in = token_data.get("expires_in", 3600)
        logger.debug("Obtained Gmail access token metadata (expires_in=%s)", expires_in)
        return access_token

    def _gmail_request(self, access_token: str, path: str) -> dict:
        """Make an authenticated request to the exact Gmail API host."""
        base = self._config_override.api_base if self._config_override else GMAIL_API_BASE
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        request = Request(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts=_GMAIL_API_HOSTS,
                timeout=30,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise GmailConnectorError(f"Gmail API request failed: HTTP {exc.code}") from None
        except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            raise GmailConnectorError(
                f"Gmail API request failed: {type(exc).__name__}"
            ) from None
        if not isinstance(body, dict):
            raise GmailConnectorError("Gmail API returned an unexpected response type")
        return body

    def list_messages(
        self,
        *,
        query: str | None = None,
        max_results: int = 100,
    ) -> tuple[GmailMessage, ...]:
        """List Gmail messages matching an optional query."""
        if not 1 <= max_results <= 500:
            raise ValueError("max_results must be between 1 and 500")

        config = self._config_override or self._acquire_config()
        access_token = self._refresh_access_token(config)
        params: dict[str, str | int] = {"maxResults": max_results}
        if query:
            params["q"] = query
        data = self._gmail_request(access_token, f"/messages?{urlencode(params)}")

        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise GmailConnectorError("Gmail messages response has an invalid shape")

        result: list[GmailMessage] = []
        for msg_ref in messages:
            if not isinstance(msg_ref, dict) or not isinstance(msg_ref.get("id"), str):
                continue
            msg = self._get_message(access_token, msg_ref["id"])
            if msg is not None:
                result.append(msg)
        return tuple(result)

    def _get_message(self, access_token: str, message_id: str) -> GmailMessage | None:
        """Fetch a single message by ID."""
        try:
            data = self._gmail_request(access_token, f"/messages/{message_id}")
        except GmailConnectorError:
            logger.warning("Failed to fetch a Gmail message by id")
            return None

        raw_headers = data.get("payload", {}).get("headers", [])
        headers = {
            item.get("name", "").lower(): item.get("value", "")
            for item in raw_headers
            if isinstance(item, dict)
        }
        return GmailMessage(
            message_id=str(data.get("id", "")),
            thread_id=str(data.get("threadId", "")),
            subject=str(headers.get("subject", "")),
            sender=str(headers.get("from", "")),
            recipients=tuple(self._parse_recipients(str(headers.get("to", "")))),
            date=str(headers.get("date", "")),
            snippet=str(data.get("snippet", "")),
        )

    def search(self, query: str, *, max_results: int = 100) -> tuple[GmailMessage, ...]:
        """Search Gmail messages by query string."""
        return self.list_messages(query=query, max_results=max_results)

    def count_unread(self) -> int:
        """Return Gmail's INBOX message count from the labels endpoint."""
        config = self._config_override or self._acquire_config()
        access_token = self._refresh_access_token(config)
        try:
            data = self._gmail_request(access_token, "/labels/INBOX")
        except GmailConnectorError:
            return 0
        total = data.get("messagesTotal", 0)
        return total if isinstance(total, int) and total >= 0 else 0

    @staticmethod
    def _parse_recipients(header_value: str) -> list[str]:
        """Parse a basic comma-separated recipient header."""
        if not header_value:
            return []
        return [addr.strip() for addr in header_value.split(",") if addr.strip()]
