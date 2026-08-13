from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from creator_app.integration_security import (
    normalize_trusted_hosts,
    open_trusted_request,
    validate_trusted_https_base_url,
)


@dataclass(frozen=True, slots=True)
class IntegrationStatus:
    integration_id: str
    configured: bool
    connected: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.integration_id,
            "configured": self.configured,
            "connected": self.connected,
            "message": self.message,
            "details": self.details,
        }


class _JsonHttpIntegration:
    def __init__(
        self,
        *,
        trusted_hosts: Iterable[str],
        timeout: int = 5,
    ) -> None:
        if not trusted_hosts:
            raise ValueError("Trusted HTTPS hosts are required for integration requests.")
        self.timeout = timeout
        self.trusted_hosts = normalize_trusted_hosts(trusted_hosts)

    def _request_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "CK-NEXUS/0.2.0",
                **(headers or {}),
            },
        )
        response_context = open_trusted_request(
            request,
            trusted_hosts=self.trusted_hosts,
            timeout=self.timeout,
        )
        with response_context as response:
            payload = response.read(512_000)
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("Unexpected integration API response")
        return decoded


class SlackIntegration(_JsonHttpIntegration):
    DEFAULT_TRUSTED_HOSTS = frozenset({"slack.com"})

    def __init__(
        self,
        token: str,
        *,
        api_base: str = "https://slack.com/api",
        timeout: int = 5,
        trusted_hosts: Iterable[str] | None = None,
    ) -> None:
        allowed_hosts = self.DEFAULT_TRUSTED_HOSTS | normalize_trusted_hosts(
            trusted_hosts or self.DEFAULT_TRUSTED_HOSTS
        )
        super().__init__(trusted_hosts=allowed_hosts, timeout=timeout)
        self.token = token.strip()
        self.api_base = validate_trusted_https_base_url(api_base, trusted_hosts=allowed_hosts)

    def status(self) -> IntegrationStatus:
        if not self.token:
            return IntegrationStatus(
                "slack", False, False, "Slack server credential is not configured."
            )
        try:
            payload = self._request_json(
                f"{self.api_base}/auth.test",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not payload.get("ok"):
                return IntegrationStatus(
                    "slack",
                    True,
                    False,
                    f"Slack authentication failed ({payload.get('error') or 'unknown_error'}).",
                )
            return IntegrationStatus(
                "slack",
                True,
                True,
                "Slack authentication verified.",
                details={
                    "workspace": payload.get("team"),
                    "bot_or_user": payload.get("user"),
                },
            )
        except HTTPError as exc:
            return IntegrationStatus("slack", True, False, f"Slack API returned HTTP {exc.code}.")
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
            return IntegrationStatus(
                "slack", True, False, "Slack API is unreachable from this runtime."
            )


class GoogleDriveIntegration(_JsonHttpIntegration):
    DEFAULT_TRUSTED_HOSTS = frozenset({"www.googleapis.com"})

    def __init__(
        self,
        access_token: str,
        *,
        api_base: str = "https://www.googleapis.com/drive/v3",
        timeout: int = 5,
        trusted_hosts: Iterable[str] | None = None,
    ) -> None:
        allowed_hosts = self.DEFAULT_TRUSTED_HOSTS | normalize_trusted_hosts(
            trusted_hosts or self.DEFAULT_TRUSTED_HOSTS
        )
        super().__init__(trusted_hosts=allowed_hosts, timeout=timeout)
        self.access_token = access_token.strip()
        self.api_base = validate_trusted_https_base_url(api_base, trusted_hosts=allowed_hosts)

    def status(self) -> IntegrationStatus:
        if not self.access_token:
            return IntegrationStatus(
                "google_drive",
                False,
                False,
                "Google Drive server credential is not configured.",
            )
        query = urlencode({"fields": "user(displayName),storageQuota(limit,usage)"})
        try:
            payload = self._request_json(
                f"{self.api_base}/about?{query}",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            user = payload.get("user") if isinstance(payload.get("user"), dict) else {}
            quota = (
                payload.get("storageQuota") if isinstance(payload.get("storageQuota"), dict) else {}
            )
            return IntegrationStatus(
                "google_drive",
                True,
                True,
                "Google Drive API access verified.",
                details={
                    "account": user.get("displayName"),
                    "quota_available": bool(quota),
                },
            )
        except HTTPError as exc:
            return IntegrationStatus(
                "google_drive", True, False, f"Google Drive API returned HTTP {exc.code}."
            )
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
            return IntegrationStatus(
                "google_drive", True, False, "Google Drive API is unreachable from this runtime."
            )
