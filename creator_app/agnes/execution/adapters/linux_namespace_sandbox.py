from __future__ import annotations

from typing import Any

from ..promotion import ArtifactPromotionState, CodePatchState
from ..request import ExecutorRiskClass, ExecutorType, SkillExecutionRequest
from ..result import ExecutionStatus, SkillExecutionResult
from ..sandbox import LinuxNamespaceRunner, PatchGuard, SandboxViolation, SandboxWorkspaceManager
from .base import ExecutionContext


class LinuxNamespaceSandboxExecutor:
    """Phase-2 local executor for bounded code patch/test/security-scan skills."""

    name = "linux_namespace_sandbox"
    executor_type = ExecutorType.SANDBOX.value
    risk_class = ExecutorRiskClass.MEDIUM

    _skills = {"hands.code_patch", "hands.test", "hands.security_scan"}

    def __init__(
        self, workspace_manager: SandboxWorkspaceManager, runner: LinuxNamespaceRunner
    ) -> None:
        self.workspaces = workspace_manager
        self.runner = runner

    async def can_handle(self, request: SkillExecutionRequest) -> bool:
        return request.executor is ExecutorType.SANDBOX and request.skill_id in self._skills

    async def health(self) -> dict[str, object]:
        health = await self.runner.health()
        return {
            **health,
            "executor": self.name,
            "skills": sorted(self._skills),
            "workspace_is_sandbox": True,
        }

    async def execute(
        self, request: SkillExecutionRequest, context: ExecutionContext
    ) -> SkillExecutionResult:
        if not request.workspace_id or not request.baseline_commit:
            return self._failed(request, "workspace_id_and_baseline_commit_required")
        if not request.idempotency_key:
            return self._failed(request, "idempotency_key_required_for_sandbox_execution")
        try:
            workspace = self.workspaces.open(request.workspace_id, request.baseline_commit)
            if request.skill_id == "hands.code_patch":
                return await self._code_patch(request, workspace)
            if request.skill_id == "hands.test":
                return await self._test(request, workspace)
            if request.skill_id == "hands.security_scan":
                return await self._security_scan(request, workspace)
            return self._failed(request, "unsupported_sandbox_skill")
        except SandboxViolation as exc:
            return self._failed(request, f"sandbox_guard:{exc}")
        except Exception as exc:
            return self._failed(request, f"sandbox_internal:{type(exc).__name__}")

    async def _code_patch(self, request: SkillExecutionRequest, workspace) -> SkillExecutionResult:
        patch = str(request.inputs.get("patch") or "")
        touched = PatchGuard.validate(patch, request.allowlist_paths)
        agnes_dir = workspace.path / ".agnes"
        agnes_dir.mkdir(parents=True, exist_ok=True)
        patch_file = agnes_dir / f"{request.execution_id}.diff"
        patch_file.write_text(patch, encoding="utf-8")
        sandbox_patch = f"/workspace/.agnes/{patch_file.name}"

        check = await self.runner.run(
            workspace=workspace.path,
            execution_id=request.execution_id + "-check",
            command=["git", "apply", "--check", sandbox_patch],
            timeout_seconds=min(request.timeout_seconds, 60),
        )
        if check.timed_out or check.returncode != 0:
            return self._command_failure(request, "patch_check_failed", check)

        applied = await self.runner.run(
            workspace=workspace.path,
            execution_id=request.execution_id + "-apply",
            command=["git", "apply", "--whitespace=nowarn", sandbox_patch],
            timeout_seconds=min(request.timeout_seconds, 60),
        )
        if applied.timed_out or applied.returncode != 0:
            return self._command_failure(request, "patch_apply_failed", applied)

        diff = self.workspaces.validate_diff(workspace, request.allowlist_paths)
        actual = set(diff["added"]) | set(diff["modified"])
        if not actual.issubset(set(touched)):
            return self._failed(request, "post_patch_diff_exceeds_declared_patch_paths")
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "workspace_id": workspace.workspace_id,
                "baseline_commit": workspace.baseline_commit,
                "changed": diff,
                "code_patch_state": CodePatchState.PATCH_APPLIED.value,
                "promotion_state": ArtifactPromotionState.CANDIDATE.value,
                "network": "denied",
                "sandbox_backend": self.runner.backend_name,
            },
            artifacts=[f"workspace:{workspace.workspace_id}:{path}" for path in sorted(actual)],
        )

    async def _test(self, request: SkillExecutionRequest, workspace) -> SkillExecutionResult:
        commands = self._commands(request.inputs.get("commands"))
        if not commands:
            commands = [("python3", "-m", "compileall", "-q", ".")]
        results: list[dict[str, Any]] = []
        for index, command in enumerate(commands, start=1):
            execution = await self.runner.run(
                workspace=workspace.path,
                execution_id=f"{request.execution_id}-test-{index}",
                command=command,
                timeout_seconds=request.timeout_seconds,
            )
            results.append(self._command_dict(command, execution))
            if execution.timed_out or execution.output_limited or execution.returncode != 0:
                return SkillExecutionResult(
                    request.execution_id,
                    request.skill_id,
                    ExecutionStatus.TIMED_OUT if execution.timed_out else ExecutionStatus.FAILED,
                    output={"commands": results, "workspace_id": workspace.workspace_id},
                    error="test_command_failed",
                )
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "commands": results,
                "workspace_id": workspace.workspace_id,
                "code_patch_state": CodePatchState.TEST.value,
                "network": "denied",
                "sandbox_backend": self.runner.backend_name,
            },
        )

    async def _security_scan(
        self, request: SkillExecutionRequest, workspace
    ) -> SkillExecutionResult:
        helper = workspace.path / ".agnes" / "phase2_secret_scan.py"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text(_SECRET_SCAN_HELPER, encoding="utf-8")
        command = ("python3", "/workspace/.agnes/phase2_secret_scan.py")
        scan = await self.runner.run(
            workspace=workspace.path,
            execution_id=request.execution_id + "-scan",
            command=command,
            timeout_seconds=request.timeout_seconds,
        )
        output = self._command_dict(command, scan)
        if scan.timed_out or scan.output_limited or scan.returncode != 0:
            return SkillExecutionResult(
                request.execution_id,
                request.skill_id,
                ExecutionStatus.TIMED_OUT if scan.timed_out else ExecutionStatus.FAILED,
                output={"scan": output, "workspace_id": workspace.workspace_id},
                error="security_scan_failed",
            )
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "scan": output,
                "workspace_id": workspace.workspace_id,
                "code_patch_state": CodePatchState.SECURITY_SCAN.value,
                "scan_status": "passed",
                "network": "denied",
                "sandbox_backend": self.runner.backend_name,
            },
        )

    @staticmethod
    def _commands(value: object) -> list[tuple[str, ...]]:
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise SandboxViolation("commands_must_be_array")
        if value and all(isinstance(item, str) for item in value):
            return [tuple(str(item) for item in value)]
        commands: list[tuple[str, ...]] = []
        for command in value:
            if not isinstance(command, (list, tuple)):
                raise SandboxViolation("command_must_be_argv_array")
            commands.append(tuple(str(item) for item in command))
        return commands

    @staticmethod
    def _command_dict(command, result) -> dict[str, object]:
        return {
            "argv": list(command),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
            "output_limited": result.output_limited,
        }

    def _command_failure(self, request, reason, result) -> SkillExecutionResult:
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.TIMED_OUT if result.timed_out else ExecutionStatus.FAILED,
            output={
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            error=reason,
        )

    @staticmethod
    def _failed(request: SkillExecutionRequest, reason: str) -> SkillExecutionResult:
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.FAILED,
            error=reason,
        )


_SECRET_SCAN_HELPER = r"""
from __future__ import annotations
import pathlib, re, sys
PATTERNS = {
    "openai": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "github": re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "slack": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
root = pathlib.Path('/workspace')
hits = []
scanned = 0
for path in root.rglob('*'):
    if not path.is_file() or path.is_symlink() or '/.agnes/' in path.as_posix():
        continue
    try: text = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError): continue
    scanned += 1
    for name, pattern in PATTERNS.items():
        if pattern.search(text): hits.append(f"{name}:{path.relative_to(root)}")
if hits:
    print(json.dumps({"status":"FAIL","scanned":scanned,"hits":hits}, sort_keys=True))
    raise SystemExit(1)
print(json.dumps({"status":"PASS","scanned":scanned,"hits":[]}, sort_keys=True))
""".replace("import pathlib, re, sys", "import json, pathlib, re, sys")
