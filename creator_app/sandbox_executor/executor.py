"""Fail-closed container sandbox executor for CK-NEXUS development assistants.

The executor is intentionally separate from ``creator_app.dev_assistants`` so the
assistant package can remain discovery/contract-only. This module is the narrow
execution kernel. It creates a disposable Git worktree, runs one digest-pinned
adapter image with network disabled, captures a bounded patch, removes the
worktree, and returns development evidence. It never applies or commits the patch.
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

from creator_app.dev_assistants import ExecutionEvidence

_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]*@sha256:[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_EXECUTION_ID_RE = re.compile(r"^devexec-[0-9a-f]{20}$")
_ALLOWED_ENGINES = frozenset({"docker", "podman"})
_ADAPTER_ENTRYPOINT = "/cknexus/adapter"


class SandboxBlocked(RuntimeError):
    """Raised when an execution request violates a fail-closed sandbox boundary."""


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    """Resource limits enforced by the container runtime."""

    timeout_seconds: int = 900
    max_patch_bytes: int = 1_000_000
    memory_bytes: int = 1_073_741_824
    cpus: float = 1.0
    pids_limit: int = 64

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        if not 1 <= self.max_patch_bytes <= 10_000_000:
            raise ValueError("max_patch_bytes must be between 1 and 10000000")
        if not 67_108_864 <= self.memory_bytes <= 8_589_934_592:
            raise ValueError("memory_bytes must be between 64 MiB and 8 GiB")
        if not 0.1 <= self.cpus <= 8.0:
            raise ValueError("cpus must be between 0.1 and 8.0")
        if not 8 <= self.pids_limit <= 512:
            raise ValueError("pids_limit must be between 8 and 512")


@dataclass(frozen=True, slots=True)
class SandboxExecutionInput:
    """Exact local inputs needed to execute a previously approved development plan."""

    plan: dict[str, Any]
    repository_path: Path
    source_sha: str
    image_ref: str
    engine: str = "docker"
    limits: SandboxLimits = SandboxLimits()


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Patch-only development result plus redacted evidence metadata."""

    execution_id: str
    assistant_id: str
    state: str
    exit_code: int | None
    patch: bytes
    patch_digest: str | None
    evidence: dict[str, Any]
    patch_applied: bool = False
    release_evidence: bool = False
    production_status: str = "NO-GO"


class SandboxExecutor:
    """Run one CK-NEXUS adapter in a disposable, network-denied container."""

    def execute(self, request: SandboxExecutionInput) -> SandboxExecutionResult:
        """Execute a validated plan and return an unverified patch artifact.

        A successful container exit is still ``EXECUTED_UNVERIFIED``. An independent
        verifier must inspect the patch before any caller may apply it.
        """
        validated = self._validate(request)
        repo = request.repository_path.expanduser().resolve()
        execution_id = validated["execution_id"]
        assistant_id = validated["assistant_id"]
        task = validated["task"]

        with tempfile.TemporaryDirectory(prefix=f"cknexus-{execution_id}-") as temp_root:
            worktree = Path(temp_root) / "worktree"
            self._add_worktree(repo, worktree, request.source_sha, request.limits)
            try:
                exit_code = self._run_container(
                    worktree=worktree,
                    execution_id=execution_id,
                    assistant_id=assistant_id,
                    task=task,
                    image_ref=request.image_ref,
                    engine=request.engine,
                    limits=request.limits,
                )
                patch = self._capture_patch(worktree, request.limits)
            finally:
                self._remove_worktree(repo, worktree, request.limits)

        patch_digest = hashlib.sha256(patch).hexdigest() if patch else None
        state = "EXECUTED_UNVERIFIED" if exit_code == 0 else "EXECUTION_FAILED"
        evidence = ExecutionEvidence(
            execution_id=execution_id,
            assistant_id=assistant_id,
            result_state=state,
            patch_digest=patch_digest,
            exit_code=exit_code,
            verifier="pending_independent_verification",
        ).envelope()
        return SandboxExecutionResult(
            execution_id=execution_id,
            assistant_id=assistant_id,
            state=state,
            exit_code=exit_code,
            patch=patch,
            patch_digest=patch_digest,
            evidence=evidence,
        )

    @staticmethod
    def _validate(request: SandboxExecutionInput) -> dict[str, str]:
        if os.name != "posix" or not hasattr(os, "getuid"):
            raise SandboxBlocked("sandbox executor requires a POSIX non-root host")
        if os.getuid() == 0:
            raise SandboxBlocked("sandbox executor refuses to run as root")
        if request.engine not in _ALLOWED_ENGINES:
            raise SandboxBlocked("container engine is not allowlisted")
        if not _IMAGE_RE.fullmatch(request.image_ref):
            raise SandboxBlocked("image_ref must be digest-pinned with @sha256:<64 hex>")
        if not _SHA1_RE.fullmatch(request.source_sha):
            raise SandboxBlocked("source_sha must be an exact lowercase 40-character Git SHA")

        repo = request.repository_path.expanduser().resolve()
        if not repo.is_dir() or not (repo / ".git").exists():
            raise SandboxBlocked("repository_path must be an existing Git repository root")

        plan = request.plan
        execution_id = str(plan.get("execution_id", ""))
        assistant_id = str(plan.get("assistant_id", "")).strip()
        task = str(plan.get("task", "")).strip()
        policy = plan.get("policy")
        if not isinstance(policy, dict):
            raise SandboxBlocked("plan policy is missing")
        if not _EXECUTION_ID_RE.fullmatch(execution_id):
            raise SandboxBlocked("plan execution_id is invalid")
        if not assistant_id:
            raise SandboxBlocked("plan assistant_id is missing")
        if not task:
            raise SandboxBlocked("plan task is missing")
        if plan.get("execution_state") != "PLANNED_NOT_EXECUTED":
            raise SandboxBlocked("plan must be in PLANNED_NOT_EXECUTED state")
        if plan.get("authority") != "CK-NEXUS":
            raise SandboxBlocked("plan authority must be CK-NEXUS")
        if plan.get("release_evidence") is not False:
            raise SandboxBlocked("development plan cannot be release evidence")
        if plan.get("production_status") != "NO-GO":
            raise SandboxBlocked("development plan must preserve Production NO-GO")
        if policy.get("isolation") != "disposable_container":
            raise SandboxBlocked("V1 executor requires disposable_container isolation")
        if policy.get("network") != "deny":
            raise SandboxBlocked("V1 executor supports network=deny only")
        if policy.get("external_mutation_authorized") is not False:
            raise SandboxBlocked("external mutation authority must remain false")
        if plan.get("credential_refs"):
            raise SandboxBlocked("V1 executor does not resolve or forward credentials")
        return {
            "execution_id": execution_id,
            "assistant_id": assistant_id,
            "task": task,
        }

    @staticmethod
    def _add_worktree(
        repo: Path,
        worktree: Path,
        source_sha: str,
        limits: SandboxLimits,
    ) -> None:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), source_sha],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=min(limits.timeout_seconds, 120),
        )
        if result.returncode != 0:
            raise SandboxBlocked("failed to create disposable Git worktree")

    @staticmethod
    def _run_container(
        *,
        worktree: Path,
        execution_id: str,
        assistant_id: str,
        task: str,
        image_ref: str,
        engine: str,
        limits: SandboxLimits,
    ) -> int:
        uid = os.getuid()
        gid = os.getgid()
        command = _container_command(
            engine=engine,
            worktree=worktree,
            execution_id=execution_id,
            assistant_id=assistant_id,
            image_ref=image_ref,
            uid=uid,
            gid=gid,
            limits=limits,
        )
        try:
            result = subprocess.run(
                command,
                check=False,
                input=task.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=limits.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxBlocked("assistant execution exceeded timeout") from exc
        return result.returncode

    @staticmethod
    def _capture_patch(worktree: Path, limits: SandboxLimits) -> bytes:
        intent = subprocess.run(
            ["git", "-C", str(worktree), "add", "-N", "--", "."],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=min(limits.timeout_seconds, 120),
        )
        if intent.returncode != 0:
            raise SandboxBlocked("failed to prepare untracked files for patch capture")

        with tempfile.NamedTemporaryFile(prefix="cknexus-patch-", suffix=".diff") as handle:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(worktree),
                    "diff",
                    "--binary",
                    "--no-ext-diff",
                    "--no-color",
                    "HEAD",
                    "--",
                    ".",
                ],
                check=False,
                stdout=handle,
                stderr=subprocess.DEVNULL,
                timeout=min(limits.timeout_seconds, 120),
            )
            if result.returncode != 0:
                raise SandboxBlocked("failed to capture sandbox patch")
            handle.flush()
            size = Path(handle.name).stat().st_size
            if size > limits.max_patch_bytes:
                raise SandboxBlocked("sandbox patch exceeds max_patch_bytes")
            handle.seek(0)
            return handle.read()

    @staticmethod
    def _remove_worktree(repo: Path, worktree: Path, limits: SandboxLimits) -> None:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=min(limits.timeout_seconds, 120),
        )


def _container_command(
    *,
    engine: str,
    worktree: Path,
    execution_id: str,
    assistant_id: str,
    image_ref: str,
    uid: int,
    gid: int,
    limits: SandboxLimits,
) -> list[str]:
    """Build the deterministic container command used by the execution kernel."""
    if engine not in _ALLOWED_ENGINES:
        raise SandboxBlocked("container engine is not allowlisted")
    if not _IMAGE_RE.fullmatch(image_ref):
        raise SandboxBlocked("container image must be digest-pinned")
    if uid <= 0 or gid < 0:
        raise SandboxBlocked("container execution requires a non-root host identity")
    mount = f"type=bind,src={worktree},dst=/workspace,rw"
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
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=67108864",
        f"--user={uid}:{gid}",
        f"--mount={mount}",
        "--workdir=/workspace",
        f"--env=CKNEXUS_EXECUTION_ID={execution_id}",
        f"--env=CKNEXUS_ASSISTANT_ID={assistant_id}",
        "-i",
        image_ref,
        _ADAPTER_ENTRYPOINT,
    ]
