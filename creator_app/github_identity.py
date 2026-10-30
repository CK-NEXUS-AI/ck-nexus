"""Minimal GitHub OAuth identity proof; access tokens are never returned or persisted."""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from creator_app.integration_security import open_trusted_request

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_EXCHANGE_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"
TRUSTED_HOSTS = frozenset({"github.com", "api.github.com"})


class GitHubIdentityError(RuntimeError):
    """Safe GitHub OAuth failure without credential material."""


@dataclass(slots=True)
class _State:
    expires_at: float


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    login: str
    user_id: int
    avatar_url: str | None
    verified_at: float


class GitHubIdentityManager:
    """One-time OAuth state and short-lived in-memory identity sessions."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        enabled: bool = True,
        state_ttl_seconds: int = 600,
        session_ttl_seconds: int = 1800,
    ) -> None:
        self.client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self.redirect_uri = redirect_uri.strip()
        self.enabled = enabled
        self.state_ttl_seconds = state_ttl_seconds
        self.session_ttl_seconds = session_ttl_seconds
        self._states: dict[str, _State] = {}
        self._sessions: dict[str, tuple[float, VerifiedIdentity]] = {}

    @property
    def configured(self) -> bool:
        return bool(
            self.enabled
            and self.client_id
            and self._client_secret
            and self.redirect_uri.startswith("https://")
        )

    def status(self, session_id: str | None = None) -> dict[str, object]:
        now = monotonic()
        self._sessions = {
            key: record for key, record in self._sessions.items() if now < record[0]
        }
        identity = None
        if session_id:
            record = self._sessions.get(session_id)
            if record:
                expires_at, candidate = record
                if now < expires_at:
                    identity = candidate
        return {
            "provider": "github",
            "configured": self.configured,
            "verified": identity is not None,
            "identity": (
                {
                    "login": identity.login,
                    "user_id": identity.user_id,
                    "avatar_url": identity.avatar_url,
                }
                if identity
                else None
            ),
            "scope": ["read:user", "user:email"],
            "credential_material_exposed": False,
            "session_ttl_seconds": self.session_ttl_seconds,
        }

    def authorization_url(self) -> str:
        if not self.configured:
            raise GitHubIdentityError("GitHub OAuth is not fully configured.")
        now = monotonic()
        self._states = {
            key: record
            for key, record in self._states.items()
            if now < record.expires_at
        }
        if len(self._states) >= 1024:
            raise GitHubIdentityError("Too many pending OAuth attempts; retry shortly.")
        state = secrets.token_urlsafe(32)
        self._states[state] = _State(now + self.state_ttl_seconds)
        return (
            f"{GITHUB_AUTHORIZE_URL}?"
            + urlencode(
                {
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "scope": "read:user user:email",
                    "state": state,
                    "allow_signup": "false",
                }
            )
        )

    def _consume_state(self, state: str) -> None:
        record = self._states.pop(state, None)
        if not record or monotonic() >= record.expires_at:
            raise GitHubIdentityError("OAuth state is invalid, expired, or already used.")

    def exchange_and_verify(self, *, code: str, state: str) -> tuple[str, VerifiedIdentity]:
        if not self.configured:
            raise GitHubIdentityError("GitHub OAuth is not fully configured.")
        if not code.strip():
            raise GitHubIdentityError("OAuth authorization code is missing.")
        self._consume_state(state)
        payload = urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            }
        ).encode("utf-8")
        request = Request(
            GITHUB_OAUTH_EXCHANGE_URL,
            data=payload,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "CK-NEXUS-Identity-Portal",
            },
        )
        try:
            with open_trusted_request(
                request, trusted_hosts=TRUSTED_HOSTS, timeout=8
            ) as response:
                token_payload = json.loads(response.read(65536).decode("utf-8"))
            token = str(token_payload.get("access_token") or "").strip()
            if not token:
                raise GitHubIdentityError("GitHub OAuth response did not include an access token.")
            profile_request = Request(
                f"{GITHUB_API_URL}/user",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "CK-NEXUS-Identity-Portal",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                method="GET",
            )
            with open_trusted_request(
                profile_request, trusted_hosts=TRUSTED_HOSTS, timeout=8
            ) as response:
                profile = json.loads(response.read(65536).decode("utf-8"))
        except GitHubIdentityError:
            raise
        except HTTPError as exc:
            raise GitHubIdentityError(f"GitHub verification failed (HTTP {exc.code}).") from None
        except (URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
            raise GitHubIdentityError("GitHub identity verification could not complete.") from exc

        login = str(profile.get("login") or "").strip()
        user_id = profile.get("id")
        if not login or isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise GitHubIdentityError("GitHub returned an incomplete identity profile.")
        identity = VerifiedIdentity(
            login=login,
            user_id=user_id,
            avatar_url=(
                str(profile["avatar_url"])
                if isinstance(profile.get("avatar_url"), str)
                and profile["avatar_url"].startswith("https://")
                else None
            ),
            verified_at=monotonic(),
        )
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = (
            monotonic() + self.session_ttl_seconds,
            identity,
        )
        return session_id, identity

    def revoke_session(self, session_id: str | None) -> None:
        if session_id:
            self._sessions.pop(session_id, None)
