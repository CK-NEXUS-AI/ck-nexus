from __future__ import annotations

import asyncio
from types import SimpleNamespace

from creator_app.agnes.execution.adapters.linux_namespace_sandbox import (
    LinuxNamespaceSandboxExecutor,
)
from creator_app.agnes.execution.result import ExecutionStatus


class RecordingRunner:
    backend_name = "test-runner"

    def __init__(self):
        self.commands = []

    async def run(self, **kwargs):
        self.commands.append(tuple(kwargs["command"]))
        return SimpleNamespace(
            returncode=0, stdout="ok", stderr="", timed_out=False, output_limited=False
        )


def test_phase3_single_command_input_reaches_sandbox_runner(tmp_path):
    executor = object.__new__(LinuxNamespaceSandboxExecutor)
    executor.runner = RecordingRunner()
    request = SimpleNamespace(
        inputs={"command": ["python3", "-c", "print('ok')"]},
        execution_id="test-execution",
        skill_id="hands.test",
        timeout_seconds=5,
    )
    workspace = SimpleNamespace(path=tmp_path, workspace_id="test-workspace")

    result = asyncio.run(executor._test(request, workspace))

    assert result.status is ExecutionStatus.SUCCEEDED
    assert executor.runner.commands == [("python3", "-c", "print('ok')")]
