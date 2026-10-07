from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.request import Request

from creator_app.credential_broker import (
    CredentialBroker,
    CredentialId,
    CredentialUnavailable,
)
from creator_app.integration_security import open_trusted_request


class GitHubAppAuthError(RuntimeError):
    """Safe GitHub App authentication error with no credential material."""


class GitHubAppAuth:
    def __init__(
        self,
        broker: CredentialBroker,
        *,
        enabled: bool,
        timeout_seconds: int = 10,
        api_version: str = "2026-03-10",
        jwt_signer: Callable[[dict[str, object], str], str] | None = None,
    ) -> None:
        self.broker = broker
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.api_version = api_version
        self._jwt_signer = jwt_signer or self._default_signer

    @property
    def configured(self) -> bool:
        required = (
            CredentialId.GITHUB_APP_ID,
            CredentialId.GITHUB_APP_PRIVATE_KEY,
            CredentialId.GITHUB_APP_INSTALLATION_ID,
        )
        return self.enabled and all(
            self.broker.is_configured(item, consumer="github.app") for item in required
        )

    @property
    def token_ready(self) -> bool:
        return self.broker.is_configured(
            CredentialId.GITHUB_INSTALLATION_TOKEN, consumer="github.app"
        )

    def status(self) -> dict[str, object]:
        return {
            "id": "github-app",
            "enabled": self.enabled,
            "configured": self.configured,
            "installation_token_ready": self.token_ready,
            "token_delivery": "credential-broker-only",
            "api_version": self.api_version,
        }

    def ensure_installation_token(self) -> dict[str, object]:
        if self.token_ready:
            return self.status()
        if not self.configured:
            raise GitHubAppAuthError("GitHub App authentication is not fully configured.")
        try:
            app_id = self.broker.acquire(CredentialId.GITHUB_APP_ID, consumer="github.app").reveal(
                consumer="github.app"
            )
            private_key = self.broker.acquire(
                CredentialId.GITHUB_APP_PRIVATE_KEY, consumer="github.app"
            ).reveal(consumer="github.app")
            installation_id = self.broker.acquire(
                CredentialId.GITHUB_APP_INSTALLATION_ID, consumer="github.app"
            ).reveal(consumer="github.app")
        except CredentialUnavailable as exc:
            raise GitHubAppAuthError("GitHub App credentials are unavailable.") from exc

        now = int(time.time())
        jwt_token = self._jwt_signer(
            {"iat": now - 60, "exp": now + 540, "iss": app_id},
            private_key,
        )
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        request = Request(
            url,
            data=b"{}",
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {jwt_token}",
                "X-GitHub-Api-Version": self.api_version,
                "Content-Type": "application/json",
                "User-Agent": "CK-NEXUS",
            },
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts={"api.github.com"},
                timeout=self.timeout_seconds,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GitHubAppAuthError("GitHub App token exchange failed safely.") from exc

        token = str(body.get("token") or "").strip()
        expires_at_raw = str(body.get("expires_at") or "").strip()
        if not token:
            raise GitHubAppAuthError("GitHub App response did not contain an installation token.")
        ttl_seconds = 3300
        if expires_at_raw:
            try:
                expiry = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
                ttl_seconds = max(60, int((expiry - datetime.now(UTC)).total_seconds()) - 30)
            except ValueError:
                ttl_seconds = 3300
        if self.broker.persistent_available:
            self.broker.put_persistent(
                CredentialId.GITHUB_INSTALLATION_TOKEN,
                token,
                source="github-app",
                ttl_seconds=ttl_seconds,
            )
        else:
            self.broker.put_ephemeral(
                CredentialId.GITHUB_INSTALLATION_TOKEN,
                token,
                source="github-app",
                ttl_seconds=ttl_seconds,
            )
        return self.status()

    @staticmethod
    def _default_signer(payload: dict[str, object], private_key: str) -> str:
        try:
            import jwt
        except ImportError as exc:
            raise GitHubAppAuthError("GitHub App JWT signing dependency is unavailable.") from exc
        # nosemgrep: python.jwt.security.audit.jwt-exposed-data.jwt-python-exposed-data -- payload is only iat/exp/iss; private key is signing material and never part of the JWT payload.
        encoded = jwt.encode(payload, private_key, algorithm="RS256")
        return str(encoded)
