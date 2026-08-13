from __future__ import annotations

import json
import shutil
# Subprocess is required only for fixed git operations against the locked repository baseline.
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path

from ..sandbox.guards import SandboxViolation
from ..sandbox.workspace import SandboxWorkspace, SandboxWorkspaceManager
from .models import WorkspaceState


@dataclass(slots=True)
class ManagedWorkspace:
    workspace: SandboxWorkspace
    state: WorkspaceState

    @property
    def workspace_id(self) -> str:
        return self.workspace.workspace_id

    @property
    def path(self) -> Path:
        return self.workspace.path

    @property
    def baseline_commit(self) -> str:
        return self.workspace.baseline_commit


class WorkspaceLifecycleManager:
    """Owns create->candidate->discard lifecycle without ever touching the source repo."""

    def __init__(self, manager: SandboxWorkspaceManager) -> None:
        self.manager = manager
        self._states: dict[str, WorkspaceState] = {}

    async def create(self, baseline_commit: str, execution_id: str) -> ManagedWorkspace:
        ws = self.manager.open(execution_id, baseline_commit)
        self._states[ws.workspace_id] = WorkspaceState.CREATED
        self._write_state(ws.path, WorkspaceState.CREATED)
        return ManagedWorkspace(ws, WorkspaceState.CREATED)

    async def checkout(self, workspace: ManagedWorkspace, commit: str) -> ManagedWorkspace:
        if commit != workspace.baseline_commit:
            raise SandboxViolation("workspace_checkout_must_match_locked_baseline")
        self._states[workspace.workspace_id] = WorkspaceState.INITIALIZED
        self._write_state(workspace.path, WorkspaceState.INITIALIZED)
        self._states[workspace.workspace_id] = WorkspaceState.READY
        self._write_state(workspace.path, WorkspaceState.READY)
        workspace.state = WorkspaceState.READY
        return workspace

    async def mark_running(self, workspace: ManagedWorkspace) -> None:
        self._states[workspace.workspace_id] = WorkspaceState.RUNNING_PIPELINE
        self._write_state(workspace.path, WorkspaceState.RUNNING_PIPELINE)
        workspace.state = WorkspaceState.RUNNING_PIPELINE

    async def mark_candidate(self, workspace: ManagedWorkspace) -> None:
        self._states[workspace.workspace_id] = WorkspaceState.CANDIDATE
        self._write_state(workspace.path, WorkspaceState.CANDIDATE)
        workspace.state = WorkspaceState.CANDIDATE

    async def get_diff(self, workspace: ManagedWorkspace) -> str:
        # Workspace is an archive, not a git worktree. Build a deterministic unified diff
        # against a temporary baseline archive by using git --no-index per changed file.
        diff = self.manager.diff(workspace.workspace)
        chunks: list[str] = []
        repo = self.manager.policy.repository_root
        git = shutil.which("git")
        if not git:
            raise RuntimeError("git_required_for_workspace_diff")
        for rel in (*diff["modified"], *diff["added"]):
            target = workspace.path / rel
            if rel in diff["added"]:
                # git is absolute from shutil.which; argv is list-based and shell is disabled.
                proc = subprocess.run(  # nosec B603
                    [git, "diff", "--no-index", "--", "/dev/null", str(target)],
                    capture_output=True,
                    text=True,
                )
            else:
                # git is absolute from shutil.which; commit/path stay separate argv elements.
                original = subprocess.run(  # nosec B603
                    [git, "-C", str(repo), "show", f"{workspace.baseline_commit}:{rel}"],
                    capture_output=True,
                    check=True,
                ).stdout
                tmp = workspace.path / ".agnes" / "baseline-diff" / rel
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(original)
                # git is absolute from shutil.which; argv is list-based and shell is disabled.
                proc = subprocess.run(  # nosec B603
                    [git, "diff", "--no-index", "--", str(tmp), str(target)],
                    capture_output=True,
                    text=True,
                )
            if proc.stdout:
                chunks.append(proc.stdout)
        return "".join(chunks)

    async def discard(self, workspace: ManagedWorkspace) -> None:
        self._states[workspace.workspace_id] = WorkspaceState.DISCARDED
        shutil.rmtree(workspace.path, ignore_errors=True)
        workspace.state = WorkspaceState.DISCARDED

    def state(self, workspace_id: str) -> WorkspaceState | None:
        return self._states.get(workspace_id)

    @staticmethod
    def _write_state(path: Path, state: WorkspaceState) -> None:
        meta = path / ".agnes"
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "lifecycle.json").write_text(
            json.dumps({"state": state.value}, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
