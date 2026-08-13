from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath


class SandboxViolation(PermissionError):
    pass


class PathGuard:
    _workspace_id = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    _forbidden_prefixes = (
        ".git",
        ".env",
        "secrets",
        "data/credential",
        "data/agnes-ledger",
    )

    @classmethod
    def validate_workspace_id(cls, workspace_id: str) -> str:
        if not cls._workspace_id.fullmatch(workspace_id):
            raise SandboxViolation("invalid_workspace_id")
        return workspace_id

    @classmethod
    def normalize_relative(cls, value: str) -> str:
        if "\x00" in value:
            raise SandboxViolation("nul_byte_denied")
        value = value.replace("\\", "/")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SandboxViolation("unsafe_relative_path")
        normalized = path.as_posix()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if any(
            normalized == prefix or normalized.startswith(prefix + "/")
            for prefix in cls._forbidden_prefixes
        ):
            raise SandboxViolation("forbidden_path")
        return normalized

    @classmethod
    def resolve_inside(
        cls, workspace: Path, relative: str, *, require_exists: bool = False
    ) -> Path:
        normalized = cls.normalize_relative(relative)
        root = workspace.resolve()
        candidate = root / normalized
        if require_exists and not candidate.exists():
            raise SandboxViolation("path_does_not_exist")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise SandboxViolation("path_escape")
        # Existing symlink components are not permitted because they can change target
        # between validation and use.
        current = root
        for part in PurePosixPath(normalized).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise SandboxViolation("symlink_path_denied")
        return candidate

    @classmethod
    def allowed(cls, relative: str, allowlist: Iterable[str]) -> bool:
        normalized = cls.normalize_relative(relative)
        patterns = tuple(allowlist)
        if not patterns:
            return False
        return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns)


class PatchGuard:
    _header = re.compile(r"^(?:---|\+\+\+)\s+([^\t\n]+)")
    _rename = re.compile(r"^(?:rename from|rename to)\s+(.+)$")

    @classmethod
    def touched_paths(cls, patch_text: str) -> tuple[str, ...]:
        if not patch_text.strip():
            raise SandboxViolation("empty_patch")
        touched: set[str] = set()
        saw_header = False
        deletion = False
        for raw in patch_text.splitlines():
            match = cls._header.match(raw)
            if match:
                saw_header = True
                path = match.group(1).strip()
                if path == "/dev/null":
                    if raw.startswith("+++ "):
                        deletion = True
                    continue
                if path.startswith("a/") or path.startswith("b/"):
                    path = path[2:]
                touched.add(PathGuard.normalize_relative(path))
                continue
            rename = cls._rename.match(raw)
            if rename:
                touched.add(PathGuard.normalize_relative(rename.group(1).strip()))
        if not saw_header:
            raise SandboxViolation("patch_missing_unified_diff_headers")
        if deletion:
            raise SandboxViolation("file_deletion_denied_phase2")
        return tuple(sorted(touched))

    @classmethod
    def validate(cls, patch_text: str, allowlist: Iterable[str]) -> tuple[str, ...]:
        touched = cls.touched_paths(patch_text)
        denied = [path for path in touched if not PathGuard.allowed(path, allowlist)]
        if denied:
            raise SandboxViolation("patch_path_not_allowlisted:" + ",".join(denied))
        return touched


class CommandGuard:
    """No shell command strings. Only argv with approved executables."""

    _allowed = {
        "python",
        "python3",
        "pytest",
        "git",
        "ruff",
        "bandit",
        "gitleaks",
    }
    _forbidden_git = {
        "push",
        "fetch",
        "pull",
        "clone",
        "remote",
        "send-email",
        "credential",
        "daemon",
    }

    @classmethod
    def validate(cls, command: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if not command or not all(isinstance(item, str) and item for item in command):
            raise SandboxViolation("command_must_be_nonempty_argv")
        if any("\x00" in item for item in command):
            raise SandboxViolation("command_nul_byte_denied")
        executable = Path(command[0]).name
        if executable not in cls._allowed:
            raise SandboxViolation(f"command_not_allowlisted:{executable}")
        if executable == "git" and len(command) > 1 and command[1] in cls._forbidden_git:
            raise SandboxViolation(f"git_subcommand_denied:{command[1]}")
        return tuple(command)
