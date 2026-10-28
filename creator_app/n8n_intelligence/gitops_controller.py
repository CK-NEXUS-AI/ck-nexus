"""Create review-only GitHub PRs for already-published, verified CK-NEXUS branches.

This controller deliberately does not run git, push, merge, or deploy. Branch
publication remains the responsibility of AutoGitOps' existing allowlisted flow.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from creator_app.n8n_intelligence.judgment_gate import JudgmentGate

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_RE = re.compile(r"^cknexus/auto-dev/[0-9a-f]{16}(?:-[0-9a-f]{12}(?:-retry-[2-5])?)?$")
_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


@dataclass(frozen=True, slots=True)
class PullRequestResult:
    state: str
    reason: str
    url: str | None = None
    number: int | None = None


class SafeGitOpsController:
    """Open an idempotent PR for an existing verified remote branch."""

    def __init__(
        self, github_token: str, github_repo: str, *, base: str = "main", timeout: float = 10.0
    ):
        if not github_token or "\n" in github_token or "\r" in github_token:
            raise ValueError("github_token_missing_or_invalid")
        if not _REPO_RE.fullmatch(github_repo):
            raise ValueError("github_repo_must_be_owner_slash_repo")
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", base) or base.startswith("-"):
            raise ValueError("base_branch_invalid")
        self._token = github_token
        self.github_repo = github_repo
        self.base = base
        self.timeout = timeout
        self.api_base = f"https://api.github.com/repos/{github_repo}"

    def create_pull_request(
        self,
        *,
        task_id: str,
        branch: str,
        commit_sha: str,
        state: str,
        tests_ok: bool,
        changed_paths: list[str],
        reason: str = "Verified automated change",
        error_reason: str | None = None,
    ) -> PullRequestResult:
        judgment = JudgmentGate().evaluate(state, tests_ok, changed_paths, error_reason)
        if judgment.action != "allow":
            return PullRequestResult("blocked", f"judgment_{judgment.action}:{judgment.reason}")
        if not _BRANCH_RE.fullmatch(branch) or not _SHA_RE.fullmatch(commit_sha):
            return PullRequestResult("blocked", "branch_or_commit_identity_invalid")
        if not task_id or len(task_id) > 128 or any(ord(c) < 32 for c in task_id):
            return PullRequestResult("blocked", "task_id_invalid")

        ref_url = f"{self.api_base}/git/ref/heads/{urllib.parse.quote(branch, safe='')}"
        remote_ref = self._request("GET", ref_url)
        remote_object = remote_ref.get("object") if isinstance(remote_ref, dict) else None
        if not isinstance(remote_object, dict) or remote_object.get("sha") != commit_sha:
            return PullRequestResult("blocked", "remote_branch_sha_mismatch")

        query = urllib.parse.urlencode(
            {
                "state": "open",
                "head": f"{self.github_repo.split('/')[0]}:{branch}",
                "base": self.base,
            }
        )
        existing = self._request("GET", f"{self.api_base}/pulls?{query}")
        if isinstance(existing, list):
            for item in existing:
                if isinstance(item, dict) and isinstance(item.get("html_url"), str):
                    return PullRequestResult(
                        "existing", "open_pr_already_exists", item["html_url"], item.get("number")
                    )

        payload = {
            "title": f"[CK-NEXUS Auto-Fix] Task {task_id}",
            "head": branch,
            "base": self.base,
            "body": (
                "Automated change from CK-NEXUS.\n\n"
                f"**Task:** `{task_id}`\n**Commit:** `{commit_sha}`\n"
                f"**Judgment:** `{judgment.action}` (TRACE L{judgment.trace_level})\n"
                f"**Reason:** {reason}\n\n"
                "Tests were reported passing by the upstream verification evidence. "
                "Please review the diff and required checks before merging."
            ),
            "draft": True,
        }
        created = self._request("POST", f"{self.api_base}/pulls", payload)
        if not isinstance(created, dict) or not isinstance(created.get("html_url"), str):
            return PullRequestResult("blocked", "github_response_missing_pr_url")
        return PullRequestResult(
            "created", "human_review_required", created["html_url"], created.get("number")
        )

    def _request(self, method: str, url: str, payload: dict[str, object] | None = None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "CK-NEXUS-Safe-GitOps",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise RuntimeError("github_response_too_large")
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            # Never include request headers, token, or raw response body in exceptions/logs.
            if exc.code == 422 and method == "POST":
                raise RuntimeError("github_pr_rejected_or_already_exists") from None
            raise RuntimeError(f"github_api_http_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise RuntimeError("github_api_unavailable_or_invalid_response") from None
