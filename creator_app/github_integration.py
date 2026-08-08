from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class GitHubStatus:
    configured: bool
    connected: bool
    login: str | None
    repository: str | None
    repository_access: bool
    default_branch: str | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "connected": self.connected,
            "login": self.login,
            "repository": self.repository,
            "repository_access": self.repository_access,
            "default_branch": self.default_branch,
            "message": self.message,
        }


class GitHubIntegration:
    """Minimal GitHub connectivity check without persisting or logging credentials."""

    def __init__(self, token: str, repository: str = "", api_base: str = "https://api.github.com") -> None:
        self._token = token.strip()
        self.repository = repository.strip().strip("/")
        self.api_base = api_base.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def _request_json(self, path: str) -> dict[str, object]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CK-NEXUS-Creator/0.2.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(f"{self.api_base}{path}", headers=headers, method="GET")
        with urlopen(request, timeout=8) as response:  # noqa: S310 - fixed HTTPS API base by default
            payload = response.read(1_048_576)
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("Unexpected GitHub API response")
        return decoded

    def status(self) -> GitHubStatus:
        if not self._token:
            return GitHubStatus(
                configured=False,
                connected=False,
                login=None,
                repository=self.repository or None,
                repository_access=False,
                default_branch=None,
                message="GITHUB_TOKEN is not configured.",
            )

        try:
            user = self._request_json("/user")
            login = str(user.get("login") or "") or None
        except HTTPError as exc:
            return GitHubStatus(
                configured=True,
                connected=False,
                login=None,
                repository=self.repository or None,
                repository_access=False,
                default_branch=None,
                message=f"GitHub authentication failed (HTTP {exc.code}).",
            )
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
            return GitHubStatus(
                configured=True,
                connected=False,
                login=None,
                repository=self.repository or None,
                repository_access=False,
                default_branch=None,
                message="GitHub API is unreachable from this runtime.",
            )

        if not self.repository:
            return GitHubStatus(
                configured=True,
                connected=True,
                login=login,
                repository=None,
                repository_access=False,
                default_branch=None,
                message="Authenticated. Set GITHUB_REPO=owner/name to verify repository access.",
            )

        safe_repo = "/".join(quote(part, safe="") for part in self.repository.split("/", 1))
        try:
            repo = self._request_json(f"/repos/{safe_repo}")
            default_branch = str(repo.get("default_branch") or "") or None
            return GitHubStatus(
                configured=True,
                connected=True,
                login=login,
                repository=self.repository,
                repository_access=True,
                default_branch=default_branch,
                message="Authenticated and repository access verified.",
            )
        except HTTPError as exc:
            return GitHubStatus(
                configured=True,
                connected=True,
                login=login,
                repository=self.repository,
                repository_access=False,
                default_branch=None,
                message=f"Authenticated, but repository access failed (HTTP {exc.code}).",
            )
        except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
            return GitHubStatus(
                configured=True,
                connected=True,
                login=login,
                repository=self.repository,
                repository_access=False,
                default_branch=None,
                message="Authenticated, but repository verification could not complete.",
            )
