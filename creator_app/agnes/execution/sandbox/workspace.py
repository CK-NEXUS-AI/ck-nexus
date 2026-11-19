from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .guards import PathGuard, SandboxViolation
from .policy import SandboxPolicy


@dataclass(frozen=True, slots=True)
class SandboxWorkspace:
    workspace_id: str
    path: Path
    baseline_commit: str
    baseline_hashes: dict[str, str]


class SandboxWorkspaceManager:
    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy
        self.workspace_root = policy.base_dir / "workspaces"
        self.runtime_root = policy.base_dir / "runtime"
        self.workspace_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.workspace_root.chmod(0o700)
        self.runtime_root.chmod(0o700)

    def open(self, workspace_id: str, baseline_commit: str) -> SandboxWorkspace:
        workspace_id = PathGuard.validate_workspace_id(workspace_id)
        if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", baseline_commit or ""):
            raise SandboxViolation("full_baseline_commit_required")
        path = self.workspace_root / workspace_id
        metadata = path / ".agnes" / "baseline.json"
        if path.exists():
            if not metadata.exists():
                raise SandboxViolation("workspace_exists_without_baseline_metadata")
            data = json.loads(metadata.read_text(encoding="utf-8"))
            if data.get("baseline_commit") != baseline_commit:
                raise SandboxViolation("workspace_baseline_mismatch")
            return SandboxWorkspace(workspace_id, path, baseline_commit, dict(data["hashes"]))

        path.mkdir(parents=True, exist_ok=False, mode=0o700)
        path.chmod(0o700)
        try:
            archive = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.policy.repository_root),
                    "archive",
                    "--format=tar",
                    baseline_commit,
                ],
                check=True,
                capture_output=True,
            ).stdout
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
                # Extract each member through Python's data filter; avoid extractall
                # so the sandbox never performs a bulk archive extraction.
                for member in tf.getmembers():
                    tf.extract(member, path, filter="data")
            self._reject_symlinks(path)
            hashes = self.hashes(path)
            (path / ".agnes").mkdir(parents=True, exist_ok=True)
            metadata.write_text(
                json.dumps(
                    {"baseline_commit": baseline_commit, "hashes": hashes},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            return SandboxWorkspace(workspace_id, path, baseline_commit, hashes)
        except Exception:
            import shutil

            shutil.rmtree(path, ignore_errors=True)
            raise

    @staticmethod
    def _reject_symlinks(workspace: Path) -> None:
        for path in workspace.rglob("*"):
            if path.is_symlink():
                raise SandboxViolation(
                    "symlink_in_workspace_denied:" + path.relative_to(workspace).as_posix()
                )

    @staticmethod
    def hashes(workspace: Path) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(workspace).as_posix()
            if relative.startswith(".agnes/"):
                continue
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            hashes[relative] = digest.hexdigest()
        return hashes

    def diff(self, workspace: SandboxWorkspace) -> dict[str, tuple[str, ...]]:
        current = self.hashes(workspace.path)
        before = workspace.baseline_hashes
        added = tuple(sorted(set(current) - set(before)))
        deleted = tuple(sorted(set(before) - set(current)))
        modified = tuple(sorted(k for k in set(before) & set(current) if before[k] != current[k]))
        return {"added": added, "modified": modified, "deleted": deleted}

    def validate_diff(
        self, workspace: SandboxWorkspace, allowlist: tuple[str, ...]
    ) -> dict[str, tuple[str, ...]]:
        self._reject_symlinks(workspace.path)
        diff = self.diff(workspace)
        if diff["deleted"]:
            raise SandboxViolation("workspace_file_deletion_denied:" + ",".join(diff["deleted"]))
        for relative in (*diff["added"], *diff["modified"]):
            PathGuard.resolve_inside(workspace.path, relative, require_exists=True)
            if not PathGuard.allowed(relative, allowlist):
                raise SandboxViolation("workspace_change_not_allowlisted:" + relative)
        return diff
