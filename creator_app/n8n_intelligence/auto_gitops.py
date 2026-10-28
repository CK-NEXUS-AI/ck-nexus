"""Publish only independently verified Auto Developer worktree branches."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from creator_app.n8n_intelligence.judgment_gate import JudgmentGate

_ALLOWED_SOURCE_PATHS = {
    "creator_app/n8n_intelligence/analysis.py",
    "creator_app/n8n_intelligence/client.py",
    "creator_app/n8n_intelligence/collector.py",
    "creator_app/n8n_intelligence/models.py",
    "creator_app/n8n_intelligence/store.py",
    "creator_app/n8n_intelligence/task_bridge.py",
    "creator_app/control_plane/fast_cache.py",
    "creator_app/control_plane/fast_probe.py",
}
_DENIED_PARTS = (
    ".env",
    "secret",
    "credential",
    ".pem",
    ".key",
    "id_rsa",
    "runtime",
    "__pycache__",
    ".pyc",
)

_PROTECTED_PATHS = {
    "creator_app/n8n_intelligence/auto_developer.py",
    "creator_app/n8n_intelligence/auto_gitops.py",
    "creator_app/n8n_intelligence/learning.py",
    "creator_app/control_plane/task_store.py",
    "creator_app/control_plane/fast_policy.py",
    "creator_app/control_plane/orchestrator.py",
    "tests/test_n8n_auto_developer.py",
    "tests/test_n8n_auto_gitops.py",
    "tests/test_n8n_agent_learning.py",
    "tests/test_control_plane_fast_policy.py",
    "tests/test_control_plane_fast_integration.py",
}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
)


@dataclass(frozen=True, slots=True)
class GitOpsRun:
    state: str
    reason: str
    job_id: str | None = None
    commit_sha: str | None = None


class AutoGitOps:
    """Commit and push verified task branches; never merge, force-push, or deploy."""

    def __init__(
        self,
        evidence_dir: str | Path,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        remote: str = "origin",
        repo_root: str | Path | None = None,
    ) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.workspace_root = self.evidence_dir.parent / "worktrees"
        self.runner = runner
        self.remote = remote
        self.repo_root = Path(repo_root) if repo_root is not None else None

    def run_once(self) -> GitOpsRun:
        if not self.evidence_dir.is_dir():
            return GitOpsRun("idle", "evidence_directory_missing")
        for path in sorted(self.evidence_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("state") != "verified":
                continue
            state = data.get("gitops_state")
            if state in {"published", "skipped", "blocked"}:
                continue
            if state in {"commit_created", "push_failed"}:
                return self._publish_committed(path, data)
            reason = self._validate_evidence(data)
            if reason:
                self._mark(path, data, gitops_state="blocked", gitops_reason=reason)
                return GitOpsRun("blocked", reason, str(data.get("job_id") or "unknown"))
            judgment = JudgmentGate().evaluate(
                str(data.get("state") or ""),
                data.get("tests_ok") is True,
                [str(item) for item in data.get("changed_paths", [])],
                str(data.get("error_reason") or data.get("error_text") or "") or None,
            )
            if judgment.action != "allow":
                reason = f"judgment_{judgment.action}:{judgment.reason}"
                self._mark(path, data, gitops_state="blocked", gitops_reason=reason)
                return GitOpsRun("blocked", reason, str(data.get("job_id") or "unknown"))
            workspace = Path(str(data["workspace"]))
            branch = str(data["branch"])
            paths = sorted(set(str(item) for item in data["changed_paths"]))
            if not paths:
                self._mark(path, data, gitops_state="skipped", gitops_reason="no_changes")
                continue
            current = self._git(["rev-parse", "HEAD"], workspace)
            if current.returncode != 0 or current.stdout.strip() != str(data["base_head"]):
                self._mark(path, data, gitops_state="blocked", gitops_reason="head_mismatch")
                return GitOpsRun("blocked", "head_mismatch", str(data.get("job_id") or "unknown"))
            status = self._git(["status", "--porcelain=v1"], workspace)
            if status.returncode != 0 or _status_paths(status.stdout) != set(paths):
                self._mark(
                    path, data, gitops_state="blocked", gitops_reason="workspace_diff_mismatch"
                )
                return GitOpsRun(
                    "blocked", "workspace_diff_mismatch", str(data.get("job_id") or "unknown")
                )
            staged = self._git(["add", "--", *paths], workspace)
            if staged.returncode != 0:
                self._mark(path, data, gitops_state="blocked", gitops_reason="git_add_failed")
                return GitOpsRun("blocked", "git_add_failed", str(data.get("job_id") or "unknown"))
            diff_check = self._git(["diff", "--cached", "--check"], workspace)
            diff_names = self._git(["diff", "--cached", "--name-only"], workspace)
            diff_text = self._git(["diff", "--cached", "--no-ext-diff", "--unified=0"], workspace)
            if any(result.returncode != 0 for result in (diff_check, diff_names, diff_text)):
                self._mark(
                    path, data, gitops_state="blocked", gitops_reason="staged_diff_check_failed"
                )
                return GitOpsRun(
                    "blocked", "staged_diff_check_failed", str(data.get("job_id") or "unknown")
                )
            staged_paths = set(diff_names.stdout.splitlines())
            if staged_paths != set(paths) or any(not _allowed_path(item) for item in staged_paths):
                self._mark(path, data, gitops_state="blocked", gitops_reason="staged_path_mismatch")
                return GitOpsRun(
                    "blocked", "staged_path_mismatch", str(data.get("job_id") or "unknown")
                )
            if any(pattern.search(diff_text.stdout) for pattern in _SECRET_PATTERNS):
                self._mark(
                    path, data, gitops_state="blocked", gitops_reason="secret_pattern_detected"
                )
                return GitOpsRun(
                    "blocked", "secret_pattern_detected", str(data.get("job_id") or "unknown")
                )
            suffix = branch.rsplit("/", 1)[-1]
            author_email = os.getenv(
                "CKNEXUS_GIT_AUTHOR_EMAIL", "cknexus-auto@users.noreply.github.com"
            )
            commit = self._git(
                [
                    "-c",
                    "user.name=CK-NEXUS Auto Developer",
                    "-c",
                    f"user.email={author_email}",
                    "commit",
                    "-m",
                    f"auto: verified development task {suffix}",
                ],
                workspace,
            )
            if commit.returncode != 0:
                self._mark(path, data, gitops_state="blocked", gitops_reason="commit_failed")
                return GitOpsRun("blocked", "commit_failed", str(data.get("job_id") or "unknown"))
            sha = self._git(["rev-parse", "HEAD"], workspace)
            if sha.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40,64}", sha.stdout.strip()):
                self._mark(
                    path, data, gitops_state="blocked", gitops_reason="commit_sha_unavailable"
                )
                return GitOpsRun(
                    "blocked", "commit_sha_unavailable", str(data.get("job_id") or "unknown")
                )
            data["commit_sha"] = sha.stdout.strip()
            data["gitops_state"] = "commit_created"
            data["gitops_reason"] = "awaiting_remote_verification"
            self._write(path, data)
            return self._publish_committed(path, data)
        return GitOpsRun("idle", "no_verified_work_pending")

    def _validate_evidence(self, data: dict[str, object]) -> str | None:
        if not all(
            data.get(key) is True
            for key in ("tests_ok", "head_unchanged", "index_clean", "safe_paths")
        ):
            return "verification_flags_missing"
        branch = str(data.get("branch") or "")
        if not re.fullmatch(
            r"cknexus/auto-dev/[0-9a-f]{16}(?:-[0-9a-f]{12}(?:-retry-[2-5])?)?", branch
        ):
            return "branch_not_allowlisted"
        try:
            workspace = Path(str(data["workspace"])).resolve(strict=True)
            root = self.workspace_root.resolve(strict=True)
            workspace.relative_to(root)
        except (KeyError, OSError, ValueError):
            return "workspace_outside_allowlist"
        paths = data.get("changed_paths")
        if not isinstance(paths, list) or any(
            not isinstance(item, str) or not _allowed_path(item) for item in paths
        ):
            return "path_not_allowlisted"
        if not data.get("base_head") or not data.get("job_id"):
            return "evidence_identity_missing"
        return None

    def _publish_committed(self, path: Path, data: dict[str, object]) -> GitOpsRun:
        workspace = Path(str(data.get("workspace") or ""))
        branch = str(data.get("branch") or "")
        expected = str(data.get("commit_sha") or "")
        if not re.fullmatch(
            r"cknexus/auto-dev/[0-9a-f]{16}(?:-[0-9a-f]{12}(?:-retry-[2-5])?)?", branch
        ) or not re.fullmatch(r"[0-9a-f]{40,64}", expected):
            self._mark(path, data, gitops_state="blocked", gitops_reason="publish_identity_invalid")
            return GitOpsRun(
                "blocked", "publish_identity_invalid", str(data.get("job_id") or "unknown")
            )
        current = self._git(["rev-parse", "HEAD"], workspace)
        if current.returncode != 0 or current.stdout.strip() != expected:
            self._mark(path, data, gitops_state="blocked", gitops_reason="commit_head_mismatch")
            return GitOpsRun(
                "blocked", "commit_head_mismatch", str(data.get("job_id") or "unknown"), expected
            )
        pushed = self._git(["push", self.remote, f"HEAD:refs/heads/{branch}"], workspace)
        if pushed.returncode != 0:
            self._mark(path, data, gitops_state="push_failed", gitops_reason="remote_push_failed")
            return GitOpsRun(
                "blocked", "remote_push_failed", str(data.get("job_id") or "unknown"), expected
            )
        remote_ref = self._git(["ls-remote", self.remote, f"refs/heads/{branch}"], workspace)
        found = (
            remote_ref.stdout.split()[0]
            if remote_ref.returncode == 0 and remote_ref.stdout.split()
            else ""
        )
        if found != expected:
            self._mark(path, data, gitops_state="push_failed", gitops_reason="remote_sha_mismatch")
            return GitOpsRun(
                "blocked", "remote_sha_mismatch", str(data.get("job_id") or "unknown"), expected
            )
        self._mark(
            path,
            data,
            gitops_state="published",
            gitops_reason="remote_sha_verified",
            push_verified=True,
        )
        # Keep the published branch, but remove its isolated checkout to save disk.
        if self.repo_root is not None:
            self._git(["worktree", "remove", "--force", str(workspace)], self.repo_root)
        return GitOpsRun(
            "published", "remote_sha_verified", str(data.get("job_id") or "unknown"), expected
        )

    def _git(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return self.runner(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30, check=False
        )

    def _mark(self, path: Path, data: dict[str, object], **updates: object) -> None:
        data.update(updates)
        self._write(path, data)

    @staticmethod
    def _write(path: Path, data: dict[str, object]) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
        )
        temporary.chmod(0o600)
        temporary.replace(path)


def _allowed_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return False
    if any(part in normalized.lower() for part in _DENIED_PARTS):
        return False
    if normalized in _PROTECTED_PATHS:
        return False
    if normalized in _ALLOWED_SOURCE_PATHS:
        return True
    if normalized.startswith("tests/") and normalized.endswith(".py"):
        return True
    return normalized.startswith("docs/") and normalized.endswith(".md")


def _status_paths(status: str) -> set[str]:
    paths: set[str] = set()
    for line in status.splitlines():
        if len(line) >= 4:
            path = line[3:].split(" -> ")[-1]
            paths.add(path)
    return paths
