from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class SandboxRequest(BaseModel):
    code: str
    language: str = "python"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    network_allowed: bool = False
    filesystem_write_allowed: bool = False


class SandboxResult(BaseModel):
    executed: bool
    success: bool
    stdout: str = ""
    stderr: str = ""
    executor_identity: str | None = None
    isolation_evidence_id: str | None = None
    reason: str | None = None


SandboxExecutor = Callable[[SandboxRequest], SandboxResult]


class SandboxRunner:
    """Policy wrapper around an externally attested sandbox executor.

    This class intentionally does not spawn subprocesses or install packages on the host.
    Real execution requires an injected executor that can provide isolation evidence.
    """

    def __init__(self, executor: SandboxExecutor | None = None) -> None:
        self._executor = executor

    def verify_request(self, request: SandboxRequest) -> dict[str, Any]:
        risks: list[str] = []
        if request.network_allowed:
            risks.append("network access requested")
        if request.filesystem_write_allowed:
            risks.append("filesystem write requested")
        return {
            "allowed_for_local_evaluation": not risks,
            "risks": risks,
            "requires_attested_executor": True,
        }

    def run(self, request: SandboxRequest) -> SandboxResult:
        policy = self.verify_request(request)
        if not policy["allowed_for_local_evaluation"]:
            return SandboxResult(
                executed=False,
                success=False,
                reason="request rejected by development sandbox policy",
            )
        if self._executor is None:
            return SandboxResult(
                executed=False,
                success=False,
                reason="no attested sandbox executor configured",
            )
        result = self._executor(request)
        if not result.executor_identity or not result.isolation_evidence_id:
            return SandboxResult(
                executed=False,
                success=False,
                reason="executor result missing identity or isolation evidence",
            )
        return result
