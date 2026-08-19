"""Independent fail-closed verifier for sandbox-generated development patches.

The verifier never trusts provider stdout or an executor success code. It consumes
only the patch artifact plus exact execution/source identities, applies structural
policy, and asks Git to validate applicability against a second disposable exact-SHA
worktree. It does not apply the patch to the canonical checkout and does not run
patched code or tests.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_ID_RE = re.compile(r"^devexec-[0-9a-f]{20}$")
_FORBIDDEN_PREFIXES = (".github/workflows/", "evidence/closure/")
_FORBIDDEN_NAMES = frozenset({".env", ".env.local", ".env.production", ".gitmodules"})


class PatchRejected(RuntimeError):
    """Raised when a patch cannot pass independent verification."""


@dataclass(frozen=True, slots=True)
class PatchVerificationPolicy:
    """Static policy applied before Git applicability verification."""

    max_patch_bytes: int = 1_000_000
    allow_binary: bool = False
    allow_symlinks: bool = False
    allow_submodules: bool = False
    forbidden_prefixes: tuple[str, ...] = _FORBIDDEN_PREFIXES
    forbidden_names: frozenset[str] = _FORBIDDEN_NAMES

    def __post_init__(self) -> None:
        if not 1 <= self.max_patch_bytes <= 10_000_000:
            raise ValueError("max_patch_bytes must be between 1 and 10000000")
        for prefix in self.forbidden_prefixes:
            if not prefix or prefix.startswith("/") or ".." in prefix.split("/"):
                raise ValueError("forbidden_prefixes must be normalized repository paths")


@dataclass(frozen=True, slots=True)
class PatchVerificationResult:
    """Independent verification result for one exact development patch."""

    verification_id: str
    execution_id: str
    assistant_id: str
    source_sha: str
    patch_digest: str
    changed_paths: tuple[str, ...]
    state: str
    evidence: dict[str, Any]
    release_evidence: bool = False
    production_status: str = "NO-GO"


class IndependentPatchVerifier:
    """Verify patch structure and exact-source applicability without executing code."""

    def verify(
        self,
        *,
        patch: bytes,
        expected_patch_digest: str,
        execution_id: str,
        assistant_id: str,
        repository_path: Path,
        source_sha: str,
        policy: PatchVerificationPolicy | None = None,
    ) -> PatchVerificationResult:
        """Return independently verified static applicability evidence."""
        effective_policy = policy or PatchVerificationPolicy()
        self._validate_identity(
            patch=patch,
            expected_patch_digest=expected_patch_digest,
            execution_id=execution_id,
            assistant_id=assistant_id,
            source_sha=source_sha,
            policy=effective_policy,
        )
        changed_paths = _inspect_patch(patch, effective_policy)
        repo = repository_path.expanduser().resolve()
        if not repo.is_dir() or not (repo / ".git").exists():
            raise PatchRejected("repository_path must be an existing Git repository root")
        if os.name != "posix" or not hasattr(os, "getuid") or os.getuid() == 0:
            raise PatchRejected("independent verifier requires a POSIX non-root host")

        self._verify_git_applicability(repo, source_sha, patch)
        patch_digest = hashlib.sha256(patch).hexdigest()
        verification_id = _verification_id(execution_id, source_sha, patch_digest)
        evidence_payload = {
            "verification_id": verification_id,
            "execution_id": execution_id,
            "assistant_id": assistant_id,
            "source_sha": source_sha,
            "patch_digest": patch_digest,
            "changed_paths": list(changed_paths),
            "state": "VERIFIED_STATIC_APPLICABLE",
            "independent_verifier": True,
            "patched_code_executed": False,
            "patch_applied_to_canonical_checkout": False,
            "raw_patch_included": False,
            "release_evidence": False,
            "production_status": "NO-GO",
            "authority": "CK-NEXUS",
        }
        encoded = _canonical_json(evidence_payload)
        evidence = {
            "verification": evidence_payload,
            "evidence_digest": hashlib.sha256(encoded).hexdigest(),
        }
        return PatchVerificationResult(
            verification_id=verification_id,
            execution_id=execution_id,
            assistant_id=assistant_id,
            source_sha=source_sha,
            patch_digest=patch_digest,
            changed_paths=changed_paths,
            state="VERIFIED_STATIC_APPLICABLE",
            evidence=evidence,
        )

    @staticmethod
    def _validate_identity(
        *,
        patch: bytes,
        expected_patch_digest: str,
        execution_id: str,
        assistant_id: str,
        source_sha: str,
        policy: PatchVerificationPolicy,
    ) -> None:
        if not patch:
            raise PatchRejected("patch must not be empty")
        if len(patch) > policy.max_patch_bytes:
            raise PatchRejected("patch exceeds max_patch_bytes")
        if not _SHA256_RE.fullmatch(expected_patch_digest):
            raise PatchRejected("expected_patch_digest must be lowercase SHA-256 hex")
        if hashlib.sha256(patch).hexdigest() != expected_patch_digest:
            raise PatchRejected("patch digest mismatch")
        if not _EXECUTION_ID_RE.fullmatch(execution_id):
            raise PatchRejected("execution_id is invalid")
        if not assistant_id.strip():
            raise PatchRejected("assistant_id must not be empty")
        if not _SHA1_RE.fullmatch(source_sha):
            raise PatchRejected("source_sha must be an exact lowercase 40-character Git SHA")

    @staticmethod
    def _verify_git_applicability(repo: Path, source_sha: str, patch: bytes) -> None:
        with tempfile.TemporaryDirectory(prefix="cknexus-verify-") as temp_root:
            worktree = Path(temp_root) / "worktree"
            added = subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), source_sha],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                env=_git_env(),
            )
            if added.returncode != 0:
                raise PatchRejected("failed to create independent verification worktree")
            try:
                checked = subprocess.run(
                    [
                        "git",
                        "-c",
                        "core.hooksPath=/dev/null",
                        "-C",
                        str(worktree),
                        "apply",
                        "--check",
                        "--whitespace=error-all",
                        "-",
                    ],
                    check=False,
                    input=patch,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                    env=_git_env(),
                )
                if checked.returncode != 0:
                    raise PatchRejected("git apply --check rejected the patch")
            finally:
                removed = subprocess.run(
                    ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                    env=_git_env(),
                )
                if removed.returncode != 0:
                    raise PatchRejected("failed to remove independent verification worktree")


def _inspect_patch(patch: bytes, policy: PatchVerificationPolicy) -> tuple[str, ...]:
    try:
        text = patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchRejected("patch must be UTF-8 text in V1") from exc
    if not policy.allow_binary and ("GIT binary patch" in text or "Binary files " in text):
        raise PatchRejected("binary patch content is not allowed")
    if not policy.allow_symlinks and "mode 120000" in text:
        raise PatchRejected("symlink changes are not allowed")
    if not policy.allow_submodules and "mode 160000" in text:
        raise PatchRejected("submodule changes are not allowed")

    changed: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("diff --git "):
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            raise PatchRejected("malformed diff header") from exc
        if len(parts) != 4 or parts[:2] != ["diff", "--git"]:
            raise PatchRejected("malformed diff header")
        left = _normalize_diff_path(parts[2], "a/")
        right = _normalize_diff_path(parts[3], "b/")
        changed.update((left, right))

    if not changed:
        raise PatchRejected("patch contains no diff --git file headers")
    for path in changed:
        _enforce_path_policy(path, policy)
    return tuple(sorted(changed))


def _normalize_diff_path(value: str, prefix: str) -> str:
    if not value.startswith(prefix):
        raise PatchRejected("diff paths must use canonical a/ and b/ prefixes")
    raw = value[len(prefix) :]
    if not raw or raw.startswith("/") or "\\" in raw:
        raise PatchRejected("diff path is not a normalized repository path")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PatchRejected("diff path contains traversal or empty segments")
    path = PurePosixPath(raw)
    if path.is_absolute() or path.parts[0] == ".git":
        raise PatchRejected("diff path targets protected Git metadata")
    return path.as_posix()


def _enforce_path_policy(path: str, policy: PatchVerificationPolicy) -> None:
    if PurePosixPath(path).name in policy.forbidden_names:
        raise PatchRejected(f"patch targets forbidden file: {path}")
    for prefix in policy.forbidden_prefixes:
        normalized = prefix.rstrip("/")
        if path == normalized or path.startswith(prefix):
            raise PatchRejected(f"patch targets forbidden path: {path}")


def _verification_id(execution_id: str, source_sha: str, patch_digest: str) -> str:
    material = f"{execution_id}:{source_sha}:{patch_digest}".encode()
    return f"devverify-{hashlib.sha256(material).hexdigest()[:20]}"


def _canonical_json(payload: dict[str, Any]) -> bytes:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env
