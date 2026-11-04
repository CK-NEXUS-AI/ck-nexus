"""Isolated dynamic verifier for statically-approved development patches.

This phase is deliberately separate from both the assistant sandbox and the static
patch verifier. It re-runs independent static verification, applies the patch only
to a fresh disposable exact-SHA worktree, and runs an explicitly trusted verifier
image with no network or credentials. Patched code never executes on the host.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creator_app.patch_verifier import IndependentPatchVerifier, PatchVerificationPolicy

from .trusted_images import trusted_verifier_image

_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]*@sha256:[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_ID_RE = re.compile(r"^devexec-[0-9a-f]{20}$")
_ALLOWED_ENGINES = frozenset({"docker", "podman"})
_ALLOWED_PROFILES = frozenset({"python_quality"})
_VERIFIER_ENTRYPOINT = "/cknexus/verify"


class DynamicVerificationBlocked(RuntimeError):
    """Raised when dynamic verification cannot satisfy its isolation contract."""


@dataclass(frozen=True, slots=True)
class DynamicVerifierLimits:
    """Resource ceilings enforced on the verifier container."""

    timeout_seconds: int = 1200
    memory_bytes: int = 2_147_483_648
    cpus: float = 2.0
    pids_limit: int = 128

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        if not 134_217_728 <= self.memory_bytes <= 8_589_934_592:
            raise ValueError("memory_bytes must be between 128 MiB and 8 GiB")
        if not 0.1 <= self.cpus <= 8.0:
            raise ValueError("cpus must be between 0.1 and 8.0")
        if not 16 <= self.pids_limit <= 512:
            raise ValueError("pids_limit must be between 16 and 512")


@dataclass(frozen=True, slots=True)
class DynamicVerificationInput:
    """Exact inputs for one isolated dynamic verification run."""

    patch: bytes
    patch_digest: str
    execution_id: str
    assistant_id: str
    repository_path: Path
    source_sha: str
    verifier_image: str
    profile: str = "python_quality"
    engine: str = "docker"
    limits: DynamicVerifierLimits = DynamicVerifierLimits()


@dataclass(frozen=True, slots=True)
class DynamicVerificationResult:
    """Dynamic verification result; still development evidence only."""

    verification_id: str
    execution_id: str
    patch_digest: str
    verifier_image: str
    profile: str
    state: str
    exit_code: int
    evidence: dict[str, Any]
    patch_applied_to_canonical_checkout: bool = False
    release_evidence: bool = False
    production_status: str = "NO-GO"


class IsolatedDynamicVerifier:
    """Run fixed verification logic against a patch in a locked-down container."""

    def verify(self, request: DynamicVerificationInput) -> DynamicVerificationResult:
        """Statically reverify, apply to disposable worktree, then run verifier image."""
        self._validate(request)
        repo = request.repository_path.expanduser().resolve()
        trusted = trusted_verifier_image(request.verifier_image, request.profile)
        if trusted is None:  # Defensive duplicate after validation.
            raise DynamicVerificationBlocked("verifier image lost trusted status")

        static_result = IndependentPatchVerifier().verify(
            patch=request.patch,
            expected_patch_digest=request.patch_digest,
            execution_id=request.execution_id,
            assistant_id=request.assistant_id,
            repository_path=repo,
            source_sha=request.source_sha,
            policy=PatchVerificationPolicy(max_patch_bytes=len(request.patch)),
        )
        if static_result.state != "VERIFIED_STATIC_APPLICABLE":
            raise DynamicVerificationBlocked("static verification did not pass")

        with tempfile.TemporaryDirectory(prefix="cknexus-dynamic-") as temp_root:
            worktree = Path(temp_root) / "worktree"
            self._add_worktree(repo, worktree, request.source_sha)
            try:
                self._apply_patch(worktree, request.patch)
                exit_code = self._run_verifier_container(request, worktree)
            finally:
                self._remove_worktree(repo, worktree)

        state = "VERIFIED_DYNAMIC" if exit_code == 0 else "DYNAMIC_VERIFICATION_FAILED"
        verification_id = _dynamic_verification_id(
            request.execution_id,
            request.source_sha,
            request.patch_digest,
            request.verifier_image,
            request.profile,
        )
        payload = {
            "verification_id": verification_id,
            "execution_id": request.execution_id,
            "assistant_id": request.assistant_id,
            "source_sha": request.source_sha,
            "patch_digest": request.patch_digest,
            "static_verification_id": static_result.verification_id,
            "verifier_image": request.verifier_image,
            "trusted_image_source_commit": trusted.source_commit,
            "trusted_image_discovery_run_id": trusted.discovery_run_id,
            "profile": request.profile,
            "state": state,
            "exit_code": exit_code,
            "network": "deny",
            "credential_forwarding": False,
            "patched_code_executed_on_host": False,
            "patch_applied_to_canonical_checkout": False,
            "release_evidence": False,
            "production_status": "NO-GO",
            "authority": "CK-NEXUS",
        }
        evidence = {
            "verification": payload,
            "evidence_digest": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        }
        return DynamicVerificationResult(
            verification_id=verification_id,
            execution_id=request.execution_id,
            patch_digest=request.patch_digest,
            verifier_image=request.verifier_image,
            profile=request.profile,
            state=state,
            exit_code=exit_code,
            evidence=evidence,
        )

    @staticmethod
    def _validate(request: DynamicVerificationInput) -> None:
        if os.name != "posix" or not hasattr(os, "getuid") or os.getuid() == 0:
            raise DynamicVerificationBlocked(
                "dynamic verifier requires a POSIX non-root host"
            )
        if not request.patch:
            raise DynamicVerificationBlocked("patch must not be empty")
        if not _SHA256_RE.fullmatch(request.patch_digest):
            raise DynamicVerificationBlocked("patch_digest must be lowercase SHA-256 hex")
        if hashlib.sha256(request.patch).hexdigest() != request.patch_digest:
            raise DynamicVerificationBlocked("patch digest mismatch")
        if not _EXECUTION_ID_RE.fullmatch(request.execution_id):
            raise DynamicVerificationBlocked("execution_id is invalid")
        if not request.assistant_id.strip():
            raise DynamicVerificationBlocked("assistant_id must not be empty")
        if not _SHA1_RE.fullmatch(request.source_sha):
            raise DynamicVerificationBlocked(
                "source_sha must be exact lowercase 40-character Git SHA"
            )
        if not _IMAGE_RE.fullmatch(request.verifier_image):
            raise DynamicVerificationBlocked("verifier_image must be digest-pinned")
        if request.engine not in _ALLOWED_ENGINES:
            raise DynamicVerificationBlocked("container engine is not allowlisted")
        if request.profile not in _ALLOWED_PROFILES:
            raise DynamicVerificationBlocked("verification profile is not allowlisted")
        if trusted_verifier_image(request.verifier_image, request.profile) is None:
            raise DynamicVerificationBlocked(
                "verifier_image is not in the CK-NEXUS trusted registry"
            )
        repo = request.repository_path.expanduser().resolve()
        if not repo.is_dir() or not (repo / ".git").exists():
            raise DynamicVerificationBlocked(
                "repository_path must be an existing Git repository root"
            )

    @staticmethod
    def _add_worktree(repo: Path, worktree: Path, source_sha: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), source_sha],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            env=_git_env(),
        )
        if result.returncode != 0:
            raise DynamicVerificationBlocked("failed to create dynamic verification worktree")

    @staticmethod
    def _apply_patch(worktree: Path, patch: bytes) -> None:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(worktree),
                "apply",
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
        if result.returncode != 0:
            raise DynamicVerificationBlocked(
                "failed to apply verified patch to disposable worktree"
            )

    @staticmethod
    def _run_verifier_container(
        request: DynamicVerificationInput,
        worktree: Path,
    ) -> int:
        command = _verifier_container_command(
            engine=request.engine,
            worktree=worktree,
            verifier_image=request.verifier_image,
            profile=request.profile,
            execution_id=request.execution_id,
            uid=os.getuid(),
            gid=os.getgid(),
            limits=request.limits,
        )
        try:
            # nosemgrep: python.django.security.injection.command.subprocess-injection -- argv is built by _verifier_container_command from allowlisted engines/profiles and digest-trusted images; shell execution is disabled.
            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=request.limits.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise DynamicVerificationBlocked("dynamic verification exceeded timeout") from exc
        return result.returncode

    @staticmethod
    def _remove_worktree(repo: Path, worktree: Path) -> None:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            env=_git_env(),
        )
        if result.returncode != 0:
            raise DynamicVerificationBlocked("failed to remove dynamic verification worktree")


def _verifier_container_command(
    *,
    engine: str,
    worktree: Path,
    verifier_image: str,
    profile: str,
    execution_id: str,
    uid: int,
    gid: int,
    limits: DynamicVerifierLimits,
) -> list[str]:
    """Build a fixed, network-denied dynamic verifier container command."""
    if engine not in _ALLOWED_ENGINES:
        raise DynamicVerificationBlocked("container engine is not allowlisted")
    if not _IMAGE_RE.fullmatch(verifier_image):
        raise DynamicVerificationBlocked("verifier image must be digest-pinned")
    if profile not in _ALLOWED_PROFILES:
        raise DynamicVerificationBlocked("verification profile is not allowlisted")
    if trusted_verifier_image(verifier_image, profile) is None:
        raise DynamicVerificationBlocked("verifier image is not trusted")
    if uid <= 0 or gid < 0:
        raise DynamicVerificationBlocked("verifier requires non-root host identity")
    mount = f"type=bind,src={worktree},dst=/workspace"
    return [
        engine,
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        f"--pids-limit={limits.pids_limit}",
        f"--memory={limits.memory_bytes}",
        f"--cpus={limits.cpus}",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=134217728",
        f"--user={uid}:{gid}",
        f"--mount={mount}",
        "--workdir=/workspace",
        f"--env=CKNEXUS_EXECUTION_ID={execution_id}",
        f"--env=CKNEXUS_VERIFY_PROFILE={profile}",
        verifier_image,
        _VERIFIER_ENTRYPOINT,
    ]


def _dynamic_verification_id(
    execution_id: str,
    source_sha: str,
    patch_digest: str,
    verifier_image: str,
    profile: str,
) -> str:
    material = ":".join((execution_id, source_sha, patch_digest, verifier_image, profile)).encode()
    return f"devdyn-{hashlib.sha256(material).hexdigest()[:20]}"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env
