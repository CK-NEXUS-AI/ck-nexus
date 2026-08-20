"""Capability-scoped read-only problem solving for the clean-room device bridge.

This module intentionally excludes shell execution, file writes, arbitrary network fetches,
credential access, and production mutation. External/mobile callers are untrusted inputs.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_MAX_TEXT_BYTES = 32_768
_MAX_JSON_BYTES = 65_536
_MAX_LIST_ENTRIES = 100

_SENSITIVE_PARTS = frozenset(
    {
        ".git",
        ".ssh",
        ".gnupg",
        ".aws",
        "credentials",
        "credential-vault",
        "secrets",
        "secret",
        "tokens",
        "token",
        "private",
    }
)
_SENSITIVE_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "auth.json",
        "credentials.json",
        "token.json",
        "id_rsa",
        "id_ed25519",
    }
)
_SENSITIVE_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".kdb", ".db", ".sqlite"})

_SECRET_REPLACEMENTS = (
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
        r"\1***REDACTED***",
    ),
    (re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{16,}\b"), "***REDACTED***"),
    (re.compile(r"(?i)\bgsk_[A-Za-z0-9]{16,}\b"), "***REDACTED***"),
    (re.compile(r"(?i)\bAIza[A-Za-z0-9_-]{16,}\b"), "***REDACTED***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "***REDACTED***"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"), "***REDACTED***"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}\b"), "***REDACTED***"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "***REDACTED***"),
    (
        re.compile(r"(?i)([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)\s*=\s*)[^\s]+"),
        r"\1***REDACTED***",
    ),
)

_DANGEROUS_CODE_PATTERNS = (
    (re.compile(r"\bos\.system\s*\("), "os.system executes a shell command"),
    (
        re.compile(r"\bsubprocess\.[A-Za-z_]+\s*\([^\n]*shell\s*=\s*True"),
        "subprocess shell=True",
    ),
    (re.compile(r"\beval\s*\("), "eval executes dynamic code"),
    (re.compile(r"\bexec\s*\("), "exec executes dynamic code"),
    (
        re.compile(r"\bpickle\.loads?\s*\("),
        "pickle load can execute attacker-controlled payloads",
    ),
)


class SolverPolicyError(ValueError):
    """Raised when a solver request violates the read-only bridge policy."""


@dataclass(frozen=True)
class WorkspaceEntry:
    """Minimized metadata for one workspace entry."""

    path: str
    kind: str
    size: int | None


def _is_sensitive_path(relative_path: Path) -> bool:
    lower_parts = tuple(part.lower() for part in relative_path.parts)
    if any(part in _SENSITIVE_PARTS for part in lower_parts):
        return True
    if not lower_parts:
        return False
    name = lower_parts[-1]
    if name in _SENSITIVE_NAMES or name.startswith(".env."):
        return True
    if "credential" in name or "secret" in name or "private_key" in name:
        return True
    return Path(name).suffix.lower() in _SENSITIVE_SUFFIXES


class SafeProblemSolver:
    """Read-only, workspace-confined problem solver for untrusted bridge clients."""

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise SolverPolicyError("workspace_root_not_directory")
        self._root = root

    @property
    def workspace_root(self) -> str:
        """Return the normalized workspace root."""
        return str(self._root)

    def _resolve(self, relative_path: str, *, require_file: bool | None = None) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise SolverPolicyError("path_required")
        if len(relative_path) > 500 or "\x00" in relative_path:
            raise SolverPolicyError("path_invalid")

        supplied = Path(relative_path)
        if supplied.is_absolute() or ".." in supplied.parts:
            raise SolverPolicyError("path_outside_workspace")
        if _is_sensitive_path(supplied):
            raise SolverPolicyError("sensitive_path_denied")

        cursor = self._root
        for part in supplied.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise SolverPolicyError("symlink_denied")

        candidate = (self._root / supplied).resolve(strict=True)
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise SolverPolicyError("path_outside_workspace") from exc

        if require_file is True and not candidate.is_file():
            raise SolverPolicyError("file_required")
        if require_file is False and not candidate.is_dir():
            raise SolverPolicyError("directory_required")
        return candidate

    def list_files(self, relative_path: str = ".") -> dict[str, Any]:
        """List bounded non-sensitive workspace metadata without reading file contents."""
        directory = self._resolve(relative_path, require_file=False)
        entries: list[WorkspaceEntry] = []
        sensitive_hidden = 0
        for item in sorted(directory.iterdir(), key=lambda value: value.name)[:_MAX_LIST_ENTRIES]:
            relative = item.relative_to(self._root)
            if _is_sensitive_path(relative):
                sensitive_hidden += 1
                continue
            if item.is_symlink():
                kind = "symlink"
                size = None
            elif item.is_dir():
                kind = "directory"
                size = None
            elif item.is_file():
                kind = "file"
                size = item.stat().st_size
            else:
                kind = "other"
                size = None
            entries.append(
                WorkspaceEntry(
                    path=relative.as_posix(),
                    kind=kind,
                    size=size,
                )
            )
        return {
            "entries": [asdict(entry) for entry in entries],
            "count": len(entries),
            "sensitive_entries_hidden": sensitive_hidden,
            "truncated": len(entries) + sensitive_hidden == _MAX_LIST_ENTRIES,
        }

    def read_text(self, relative_path: str) -> dict[str, Any]:
        """Read a bounded text file, redact credential-like values, and return a digest."""
        path = self._resolve(relative_path, require_file=True)
        size = path.stat().st_size
        if size > _MAX_TEXT_BYTES:
            raise SolverPolicyError("file_too_large")

        raw = path.read_bytes()
        if b"\x00" in raw:
            raise SolverPolicyError("binary_file_denied")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SolverPolicyError("non_utf8_file_denied") from exc

        if "PRIVATE KEY-----" in text:
            redacted = "***REDACTED_SENSITIVE_CONTENT***"
        else:
            redacted = redact_text(text)
        return {
            "path": path.relative_to(self._root).as_posix(),
            "size": size,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content": redacted,
            "redacted": redacted != text,
        }

    def sha256_file(self, relative_path: str) -> dict[str, Any]:
        """Hash a bounded non-sensitive workspace file without returning its contents."""
        path = self._resolve(relative_path, require_file=True)
        digest = hashlib.sha256()
        total = 0
        with path.open("rb") as handle:
            while chunk := handle.read(65_536):
                total += len(chunk)
                if total > 16 * 1024 * 1024:
                    raise SolverPolicyError("hash_file_too_large")
                digest.update(chunk)
        return {
            "path": path.relative_to(self._root).as_posix(),
            "size": total,
            "sha256": digest.hexdigest(),
        }

    def analyze_json(self, data: str) -> dict[str, Any]:
        """Parse bounded JSON and return structure-only metadata plus a digest."""
        if not isinstance(data, str):
            raise SolverPolicyError("json_input_must_be_string")
        encoded = data.encode("utf-8")
        if len(encoded) > _MAX_JSON_BYTES:
            raise SolverPolicyError("json_input_too_large")
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            return {
                "valid": False,
                "error": f"json_decode_error:{exc.msg}",
                "sha256": hashlib.sha256(encoded).hexdigest(),
            }

        result: dict[str, Any] = {
            "valid": True,
            "type": type(parsed).__name__,
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
        if isinstance(parsed, dict):
            result["keys"] = sorted(str(key) for key in parsed)[:100]
            result["count"] = len(parsed)
        elif isinstance(parsed, list):
            result["count"] = len(parsed)
        return result

    def review_code(self, code: str) -> dict[str, Any]:
        """Perform deterministic non-executing review for dangerous primitives."""
        if not isinstance(code, str):
            raise SolverPolicyError("code_must_be_string")
        encoded = code.encode("utf-8")
        if len(encoded) > _MAX_JSON_BYTES:
            raise SolverPolicyError("code_too_large")

        findings: list[dict[str, Any]] = []
        for pattern, message in _DANGEROUS_CODE_PATTERNS:
            for match in pattern.finditer(code):
                findings.append({"offset": match.start(), "message": message})
        return {
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "finding_count": len(findings),
            "findings": findings[:100],
            "executed": False,
        }


def redact_text(text: str) -> str:
    """Redact common credential forms before data leaves the workspace boundary."""
    redacted = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
