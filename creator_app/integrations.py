from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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
    def __init__(self, *, timeout: int = 5) -> None:
        self.timeout = timeout

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
        with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - trusted server configuration
            payload = response.read(512_000)
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("Unexpected integration API response")
        return decoded


class SlackIntegration(_JsonHttpIntegration):
    def __init__(self, token: str, *, api_base: str = "https://slack.com/api", timeout: int = 5) -> None:
        super().__init__(timeout=timeout)
        self.token = token.strip()
        self.api_base = api_base.rstrip("/")

    def status(self) -> IntegrationStatus:
        if not self.token:
            return IntegrationStatus("slack", False, False, "Slack server credential is not configured.")
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
            return IntegrationStatus("slack", True, False, "Slack API is unreachable from this runtime.")


class GoogleDriveIntegration(_JsonHttpIntegration):
    def __init__(
        self,
        access_token: str,
        *,
        api_base: str = "https://www.googleapis.com/drive/v3",
        timeout: int = 5,
    ) -> None:
        super().__init__(timeout=timeout)
        self.access_token = access_token.strip()
        self.api_base = api_base.rstrip("/")

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
            quota = payload.get("storageQuota") if isinstance(payload.get("storageQuota"), dict) else {}
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


class N8nIntegration(_JsonHttpIntegration):
    def __init__(self, base_url: str, api_key: str, *, timeout: int = 5) -> None:
        super().__init__(timeout=timeout)
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()

    def status(self) -> IntegrationStatus:
        if not self.base_url:
            return IntegrationStatus("n8n", False, False, "n8n instance URL is not configured.")
        if not self.api_key:
            return IntegrationStatus(
                "n8n",
                True,
                False,
                "n8n API credential is not configured; instance URL is present but API access is unverified.",
                details={"base_url_configured": True},
            )
        try:
            payload = self._request_json(
                f"{self.base_url}/api/v1/workflows?limit=1",
                headers={"X-N8N-API-KEY": self.api_key},
            )
            return IntegrationStatus(
                "n8n",
                True,
                True,
                "n8n Public API access verified.",
                details={"workflow_list_shape_valid": "data" in payload},
            )
        except HTTPError as exc:
            return IntegrationStatus("n8n", True, False, f"n8n API returned HTTP {exc.code}.")
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
            return IntegrationStatus("n8n", True, False, "n8n API is unreachable from this runtime.")
