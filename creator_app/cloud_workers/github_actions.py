"""GitHub-hosted validation worker with fixed tasks and least-privilege credentials.

This adapter dispatches only a repository-owned workflow. It never accepts shell
commands, arbitrary workflow names, or arbitrary repositories from task callers.
"""

from __future__ import annotations

import json
import re
import uuid
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request

from creator_app.credential_broker import CredentialBroker, CredentialId
from creator_app.github_app import GitHubAppAuth, GitHubAppAuthError
from creator_app.integration_security import open_trusted_request

_ALLOWED_TASKS = frozenset({"tests", "security", "full_validation"})
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_WORKFLOW_FILE = "cknexus-cloud-worker.yml"
_WORKFLOW_NAME = "CK-NEXUS Cloud Worker"
_API_ROOT = "https://api.github.com"


class CloudWorkerError(RuntimeError):
    """Sanitized cloud-worker error; never contains credential material."""


class GitHubActionsCloudWorker:
    """Dispatch and inspect fixed validation jobs on GitHub-hosted runners."""

    def __init__(
        self,
        *,
        broker: CredentialBroker,
        github_app_auth: GitHubAppAuth,
        enabled: bool = False,
        repository: str = "CK-NEXUS-AI/ck-nexus",
        default_ref: str = "main",
        workflow_file: str = _WORKFLOW_FILE,
        api_version: str = "2026-03-10",
        timeout_seconds: int = 15,
    ) -> None:
        if not _REPOSITORY_RE.fullmatch(repository):
            raise ValueError("repository must be owner/name")
        owner, name = repository.split("/", 1)
        if owner in {".", ".."} or name in {".", ".."}:
            raise ValueError("repository must be owner/name")
        if workflow_file != _WORKFLOW_FILE:
            raise ValueError("workflow_file is fixed by the CK-NEXUS cloud-worker policy")
        if default_ref != "main":
            raise ValueError("cloud worker dispatch ref is fixed to main")
        if not 1 <= timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 1 and 30")
        self.broker = broker
        self.github_app_auth = github_app_auth
        self.enabled = enabled
        self.repository = repository
        self.default_ref = default_ref
        self.workflow_file = workflow_file
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds

    def status(self) -> dict[str, object]:
        auth = self.github_app_auth.status()
        return {
            "provider": "github_actions",
            "enabled": self.enabled,
            "configured": bool(auth.get("configured") or auth.get("installation_token_ready")),
            "authentication": "credential_broker",
            "workflow": self.workflow_file,
            "repository": self.repository,
            "default_ref": self.default_ref,
            "allowed_tasks": sorted(_ALLOWED_TASKS),
            "execution_location": "github_hosted_runner",
            "arbitrary_shell_allowed": False,
            "repository_write_permission_requested": False,
            "external_mutation_authorized": False,
            "production_status": "NO-GO",
            "q10_status": "NOT_VERIFIED",
        }

    def dispatch(self, *, task_kind: str, subject_sha: str) -> dict[str, object]:
        if not self.enabled:
            raise CloudWorkerError("Cloud worker dispatch is disabled by configuration.")
        if task_kind not in _ALLOWED_TASKS:
            raise ValueError("task_kind is not an allowed fixed cloud-worker task")
        if not isinstance(subject_sha, str) or not _SHA_RE.fullmatch(subject_sha):
            raise ValueError("subject_sha must be a full lowercase 40-character Git commit SHA")

        try:
            self.github_app_auth.ensure_installation_token()
            lease = self.broker.acquire(
                CredentialId.GITHUB_INSTALLATION_TOKEN,
                consumer="github.app",
            )
            token = lease.reveal(consumer="github.app")
        except (GitHubAppAuthError, ValueError, RuntimeError, PermissionError) as exc:
            raise CloudWorkerError("GitHub App authentication is unavailable.") from exc

        request_id = uuid.uuid4().hex
        url = (
            f"{_API_ROOT}/repos/{self.repository}/actions/workflows/"
            f"{quote(self.workflow_file, safe='')}/dispatches"
        )
        payload = {
            "ref": self.default_ref,
            "inputs": {
                "request_id": request_id,
                "task_kind": task_kind,
                "subject_sha": subject_sha,
            },
        }
        request = Request(
            url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers=self._headers(token, json_body=True),
        )
        try:
            with open_trusted_request(
                request,
                trusted_hosts={"api.github.com"},
                timeout=self.timeout_seconds,
            ) as response:
                response_status = int(getattr(response, "status", 204))
                if response_status not in {200, 201, 202, 204}:
                    raise CloudWorkerError(
                        f"GitHub Actions dispatch returned HTTP {response_status}."
                    )
        except HTTPError as exc:
            raise CloudWorkerError(
                f"GitHub Actions dispatch was rejected (HTTP {exc.code})."
            ) from None
        except CloudWorkerError:
            raise
        except Exception as exc:
            raise CloudWorkerError("GitHub Actions dispatch failed safely.") from exc

        return {
            "ok": True,
            "state": "submitted",
            "request_id": request_id,
            "task_kind": task_kind,
            "subject_sha": subject_sha,
            "workflow": self.workflow_file,
            "repository": self.repository,
            "execution_location": "github_hosted_runner",
            "evidence_expected": True,
            "external_mutation_authorized": False,
            "release_evidence": False,
            "production_status": "NO-GO",
            "q10_status": "NOT_VERIFIED",
        }

    def get_result(self, *, request_id: str) -> dict[str, object]:
        if not _REQUEST_ID_RE.fullmatch(request_id):
            raise ValueError("request_id must be a 32-character lowercase hex identifier")
        token = self._token()
        query = urlencode({"event": "workflow_dispatch", "per_page": 100})
        url = (
            f"{_API_ROOT}/repos/{self.repository}/actions/workflows/"
            f"{quote(self.workflow_file, safe='')}/runs?{query}"
        )
        data = self._get_json(url, token)
        expected_title = f"{_WORKFLOW_NAME} {request_id}"
        run = next(
            (
                item
                for item in data.get("workflow_runs", [])
                if isinstance(item, dict) and item.get("display_title") == expected_title
            ),
            None,
        )
        if run is None:
            return {
                "ok": True,
                "state": "accepted_pending_discovery",
                "request_id": request_id,
                "workflow": self.workflow_file,
                "evidence_available": False,
                "external_mutation_authorized": False,
                "release_evidence": False,
                "production_status": "NO-GO",
            }

        return {
            "ok": True,
            "state": run.get("status", "unknown"),
            "conclusion": run.get("conclusion"),
            "request_id": request_id,
            "run_id": run.get("id"),
            "run_url": run.get("html_url"),
            "head_sha": run.get("head_sha"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "evidence_available": run.get("status") == "completed",
            "external_mutation_authorized": False,
            "release_evidence": False,
            "production_status": "NO-GO",
        }

    def _token(self) -> str:
        try:
            self.github_app_auth.ensure_installation_token()
            lease = self.broker.acquire(
                CredentialId.GITHUB_INSTALLATION_TOKEN,
                consumer="github.app",
            )
            return lease.reveal(consumer="github.app")
        except (GitHubAppAuthError, ValueError, RuntimeError, PermissionError) as exc:
            raise CloudWorkerError("GitHub App authentication is unavailable.") from exc

    def _headers(self, token: str, *, json_body: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "CK-NEXUS-Cloud-Worker",
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _get_json(self, url: str, token: str) -> dict[str, object]:
        request = Request(url, headers=self._headers(token), method="GET")
        try:
            with open_trusted_request(
                request,
                trusted_hosts={"api.github.com"},
                timeout=self.timeout_seconds,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise CloudWorkerError(
                f"GitHub Actions status lookup failed (HTTP {exc.code})."
            ) from None
        except Exception as exc:
            raise CloudWorkerError("GitHub Actions status lookup failed safely.") from exc
        if not isinstance(body, dict):
            raise CloudWorkerError("GitHub Actions returned an invalid status response.")
        return body
