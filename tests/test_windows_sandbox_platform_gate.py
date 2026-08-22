from __future__ import annotations

import asyncio

import pytest

from creator_app.agnes.execution.sandbox import runner as runner_module
from creator_app.agnes.execution.sandbox.guards import SandboxViolation
from creator_app.agnes.execution.sandbox.policy import SandboxPolicy


def test_non_linux_runner_is_import_safe_and_fail_closed(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runner_module, "_IS_LINUX", False)
    monkeypatch.setattr(runner_module, "_resource", None)

    policy = SandboxPolicy(base_dir=tmp_path / "sandbox", repository_root=tmp_path)
    runner = runner_module.LinuxNamespaceRunner(policy)

    assert runner.platform_supported is False
    assert runner.unshare is None

    health = asyncio.run(runner.health())
    assert health == {
        "ready": False,
        "backend": "linux_namespace_chroot",
        "production_safe": False,
        "reason": "linux_namespace_not_supported",
    }

    with pytest.raises(SandboxViolation, match="linux_namespace_not_supported"):
        asyncio.run(
            runner.run(
                workspace=tmp_path,
                execution_id="windows-negative-test",
                command=["python", "-V"],
                timeout_seconds=1,
            )
        )


def test_resource_limit_guard_fails_closed_without_resource(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(runner_module, "_IS_LINUX", True)
    monkeypatch.setattr(runner_module, "_resource", None)

    policy = SandboxPolicy(base_dir=tmp_path / "sandbox", repository_root=tmp_path)
    runner = runner_module.LinuxNamespaceRunner(policy)

    assert runner.platform_supported is False
    with pytest.raises(SandboxViolation, match="linux_resource_limits_not_supported"):
        runner._limits()
