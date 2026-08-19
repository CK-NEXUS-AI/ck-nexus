"""Tests for the CK-NEXUS container sandbox executor."""

from pathlib import Path

import pytest

from creator_app.dev_assistants import (
    DevExecutionContract,
    ExecutionPolicy,
    ExecutionRequest,
    IsolationMode,
    NetworkMode,
)
from creator_app.sandbox_executor import executor as executor_module
from creator_app.sandbox_executor.executor import (
    SandboxBlocked,
    SandboxExecutionInput,
    SandboxExecutor,
    SandboxLimits,
    _container_command,
)

_IMAGE = "ghcr.io/cknexus/aider-adapter@sha256:" + "a" * 64
_SOURCE_SHA = "1" * 40


def _plan(
    *,
    network: NetworkMode = NetworkMode.DENY,
    credential_refs: tuple[str, ...] = (),
) -> dict:
    request = ExecutionRequest(
        assistant_id="aider",
        task="Inspect the repository and produce a minimal patch.",
        workstream_id="ws-test",
        required_capabilities=("code_edit",),
        credential_refs=credential_refs,
    )
    policy = ExecutionPolicy(
        isolation=IsolationMode.DISPOSABLE_CONTAINER,
        network=network,
    )
    return DevExecutionContract().build_plan(request, policy)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo


def _non_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(executor_module.os, "getuid", lambda: 1000)
    monkeypatch.setattr(executor_module.os, "getgid", lambda: 1000)


def test_plan_carries_normalized_execution_identity() -> None:
    plan = _plan()
    assert plan["task"] == "Inspect the repository and produce a minimal patch."
    assert plan["workstream_id"] == "ws-test"
    assert plan["execution_id"].startswith("devexec-")
    assert len(plan["request_digest"]) == 64
    assert plan["policy"]["network"] == "deny"
    assert plan["policy"]["isolation"] == "disposable_container"


def test_container_command_enforces_hardening_flags(tmp_path: Path) -> None:
    command = _container_command(
        engine="docker",
        worktree=tmp_path / "worktree",
        execution_id="devexec-" + "b" * 20,
        assistant_id="aider",
        image_ref=_IMAGE,
        uid=1000,
        gid=1000,
        limits=SandboxLimits(),
    )
    assert "--pull=never" in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--user=1000:1000" in command
    assert "/cknexus/adapter" == command[-1]
    assert "--privileged" not in command
    assert all("docker.sock" not in item for item in command)


def test_validate_accepts_exact_network_denied_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _non_root(monkeypatch)
    request = SandboxExecutionInput(
        plan=_plan(),
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref=_IMAGE,
    )
    validated = SandboxExecutor._validate(request)
    assert validated["assistant_id"] == "aider"
    assert validated["execution_id"].startswith("devexec-")


def test_validate_rejects_unpinned_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _non_root(monkeypatch)
    request = SandboxExecutionInput(
        plan=_plan(),
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref="ghcr.io/cknexus/aider-adapter:latest",
    )
    with pytest.raises(SandboxBlocked, match="digest-pinned"):
        SandboxExecutor._validate(request)


def test_validate_rejects_brokered_network_until_separate_adapter_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _non_root(monkeypatch)
    request = SandboxExecutionInput(
        plan=_plan(network=NetworkMode.BROKERED),
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref=_IMAGE,
    )
    with pytest.raises(SandboxBlocked, match="network=deny only"):
        SandboxExecutor._validate(request)


def test_validate_rejects_credential_forwarding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _non_root(monkeypatch)
    request = SandboxExecutionInput(
        plan=_plan(credential_refs=("cred://openai/dev",)),
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref=_IMAGE,
    )
    with pytest.raises(SandboxBlocked, match="does not resolve or forward credentials"):
        SandboxExecutor._validate(request)


def test_validate_rejects_tampered_task_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _non_root(monkeypatch)
    plan = _plan()
    plan["task"] = "Tampered after approval"
    request = SandboxExecutionInput(
        plan=plan,
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref=_IMAGE,
    )
    with pytest.raises(SandboxBlocked, match="request_digest"):
        SandboxExecutor._validate(request)


def test_validate_refuses_root_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(executor_module.os, "getuid", lambda: 0)
    request = SandboxExecutionInput(
        plan=_plan(),
        repository_path=_repo(tmp_path),
        source_sha=_SOURCE_SHA,
        image_ref=_IMAGE,
    )
    with pytest.raises(SandboxBlocked, match="refuses to run as root"):
        SandboxExecutor._validate(request)


def test_limits_fail_closed() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        SandboxLimits(timeout_seconds=0)
    with pytest.raises(ValueError, match="max_patch_bytes"):
        SandboxLimits(max_patch_bytes=20_000_000)
