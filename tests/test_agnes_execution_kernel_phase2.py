from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from creator_app.agnes.execution.idempotency import SQLiteIdempotencyStore
from creator_app.agnes.execution.result import ExecutionStatus
from creator_app.agnes.execution.sandbox import (
    LinuxNamespaceRunner,
    SandboxPolicy,
    SandboxViolation,
)
from creator_app.agnes_runtime import AgnesNervousSystem
from tests.omni_context_factory import make_test_omni_context

REPO = Path(__file__).resolve().parents[1]
SKILL_FILE = REPO / "creator_app" / "skills" / "agnes" / "SKILL.md"
BASELINE = "8f37036d73e2172fd74dd9687bc2e1264c248fdc"


def _agnes(tmp_path: Path) -> AgnesNervousSystem:
    return AgnesNervousSystem(
        skill_file=SKILL_FILE,
        ledger_path=tmp_path / "ledger.jsonl",
        sandbox_enabled=True,
        sandbox_root=tmp_path / "sandbox",
        sandbox_repository_root=REPO,
        execution_context_factory=make_test_omni_context,
    )


def test_python_alias_resolves_to_trusted_system_python_when_missing(monkeypatch, tmp_path: Path):
    runner = LinuxNamespaceRunner(
        SandboxPolicy(base_dir=tmp_path / "runtime", repository_root=REPO)
    )
    monkeypatch.setattr("creator_app.agnes.execution.sandbox.runner.shutil.which", lambda _: None)
    resolved = runner._resolve_executable(("python", "-c", "print(1)"))
    assert resolved[0] in {
        "/opt/pyvenv/bin/python",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
        "/bin/python3",
    }
    assert Path(resolved[0]).is_file()


def _patch_request(*, approval_id: str | None = None, workspace_id: str = "ws-phase2") -> dict:
    patch = (
        "--- /dev/null\n"
        "+++ b/phase2_sandbox_probe.py\n"
        "@@ -0,0 +1,2 @@\n"
        '+print("phase2-ok")\n'
        "+VALUE = 42\n"
    )
    return {
        "id": "hands.code_patch",
        "executor": "sandbox",
        "inputs": {"patch": patch},
        "allowlist_paths": ["phase2_sandbox_probe.py"],
        "granted_capabilities": ["code_write", "patch"],
        "execution_id": "exec-patch-phase2",
    }


@pytest.mark.asyncio
async def test_linux_namespace_runner_isolates_network_and_host_root(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    script = work / "probe.py"
    script.write_text(
        "import pathlib, socket\n"
        "print('etc-visible', pathlib.Path('/etc/passwd').exists())\n"
        "s=socket.socket(); s.settimeout(0.2)\n"
        "try:\n s.connect(('1.1.1.1',80)); print('network-open')\n"
        "except Exception as e:\n print('network-blocked', type(e).__name__)\n",
        encoding="utf-8",
    )
    runner = LinuxNamespaceRunner(
        SandboxPolicy(base_dir=tmp_path / "runtime", repository_root=REPO)
    )
    health = await runner.health()
    assert health["ready"] is True
    result = await runner.run(
        workspace=work,
        execution_id="probe",
        command=["python", "/workspace/probe.py"],
        timeout_seconds=10,
    )
    assert result.returncode == 0
    assert "etc-visible False" in result.stdout
    assert "network-blocked" in result.stdout
    assert "network-open" not in result.stdout


@pytest.mark.asyncio
async def test_timeout_kills_process_group(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    runner = LinuxNamespaceRunner(
        SandboxPolicy(base_dir=tmp_path / "runtime", repository_root=REPO, kill_grace_seconds=0.2)
    )
    code = (
        "import subprocess,time; "
        "subprocess.Popen(['python','-c',\"import time,pathlib; time.sleep(2); "
        "pathlib.Path('/workspace/child-survived').write_text('bad')\"]); "
        "time.sleep(20)"
    )
    result = await runner.run(
        workspace=work,
        execution_id="timeout",
        command=["python", "-c", code],
        timeout_seconds=1,
    )
    assert result.timed_out is True
    await asyncio.sleep(3)
    assert not (work / "child-survived").exists()


@pytest.mark.asyncio
async def test_runtime_fails_closed_without_omni_context_factory(tmp_path: Path):
    agnes = AgnesNervousSystem(
        skill_file=SKILL_FILE,
        ledger_path=tmp_path / "ledger-no-omni.jsonl",
        sandbox_enabled=True,
        sandbox_root=tmp_path / "sandbox-no-omni",
        sandbox_repository_root=REPO,
    )
    result = await agnes.execute_skill(
        _patch_request(),
        goal="fail closed without trusted OMNI context",
        correlation_id="corr-no-omni",
        workspace_id="ws-no-omni",
        baseline_commit=BASELINE,
        idempotency_key="idem-no-omni",
    )
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "omni_context_required"


@pytest.mark.asyncio
async def test_code_patch_requires_sticky_approval_then_runs_in_sandbox(tmp_path: Path):
    agnes = _agnes(tmp_path)
    step = _patch_request()
    waiting = await agnes.execute_skill(
        step,
        goal="add isolated probe",
        correlation_id="corr-p2",
        workspace_id="ws-phase2",
        baseline_commit=BASELINE,
        idempotency_key="patch-1",
    )
    assert waiting.status is ExecutionStatus.WAITING_APPROVAL
    assert waiting.approval_fingerprint

    agnes.approvals.grant(
        approval_id="approve-p2",
        fingerprint=waiting.approval_fingerprint,
        approved_by="human",
    )
    result = await agnes.execute_skill(
        step,
        goal="add isolated probe",
        correlation_id="corr-p2",
        workspace_id="ws-phase2",
        baseline_commit=BASELINE,
        approval_id="approve-p2",
        idempotency_key="patch-1",
    )
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output["network"] == "denied"
    assert result.output["sandbox_backend"] == "linux_namespace_chroot"
    assert result.output["changed"]["added"] == ["phase2_sandbox_probe.py"]


@pytest.mark.asyncio
async def test_test_and_security_scan_run_on_same_isolated_workspace(tmp_path: Path):
    agnes = _agnes(tmp_path)
    step = _patch_request(workspace_id="ws-chain")
    waiting = await agnes.execute_skill(
        step,
        goal="patch test chain",
        correlation_id="corr-chain",
        workspace_id="ws-chain",
        baseline_commit=BASELINE,
        idempotency_key="patch-chain",
    )
    agnes.approvals.grant(
        approval_id="approve-chain",
        fingerprint=waiting.approval_fingerprint or "",
        approved_by="human",
    )
    patched = await agnes.execute_skill(
        step,
        goal="patch test chain",
        correlation_id="corr-chain",
        workspace_id="ws-chain",
        baseline_commit=BASELINE,
        approval_id="approve-chain",
        idempotency_key="patch-chain",
    )
    assert patched.status is ExecutionStatus.SUCCEEDED

    tested = await agnes.execute_skill(
        {
            "id": "hands.test",
            "executor": "sandbox",
            "inputs": {"commands": [["python", "/workspace/phase2_sandbox_probe.py"]]},
            "granted_capabilities": ["test", "shell"],
            "execution_id": "exec-test-phase2",
        },
        goal="test patch",
        correlation_id="corr-test",
        workspace_id="ws-chain",
        baseline_commit=BASELINE,
        idempotency_key="test-chain",
    )
    assert tested.status is ExecutionStatus.SUCCEEDED
    assert "phase2-ok" in tested.output["commands"][0]["stdout"]

    scanned = await agnes.execute_skill(
        {
            "id": "hands.security_scan",
            "executor": "sandbox",
            "inputs": {},
            "granted_capabilities": ["security_scan", "shell"],
            "execution_id": "exec-scan-phase2",
        },
        goal="scan patch",
        correlation_id="corr-scan",
        workspace_id="ws-chain",
        baseline_commit=BASELINE,
        idempotency_key="scan-chain",
    )
    assert scanned.status is ExecutionStatus.SUCCEEDED
    assert '"status": "PASS"' in scanned.output["scan"]["stdout"]


@pytest.mark.asyncio
async def test_patch_path_escape_and_delete_are_denied(tmp_path: Path):
    agnes = _agnes(tmp_path)
    bad_patches = [
        "--- /dev/null\n+++ b/../escape.py\n@@ -0,0 +1 @@\n+x=1\n",
        "--- a/README.md\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n",
    ]
    for index, patch in enumerate(bad_patches):
        result = await agnes.execute_skill(
            {
                "id": "hands.code_patch",
                "executor": "sandbox",
                "inputs": {"patch": patch},
                "allowlist_paths": ["**"],
                "granted_capabilities": ["code_write", "patch"],
                "execution_id": f"bad-{index}",
            },
            goal="bad patch",
            correlation_id=f"bad-corr-{index}",
            workspace_id=f"bad-ws-{index}",
            baseline_commit=BASELINE,
            idempotency_key=f"bad-idem-{index}",
        )
        assert result.status is ExecutionStatus.WAITING_APPROVAL
        agnes.approvals.grant(
            approval_id=f"bad-approval-{index}",
            fingerprint=result.approval_fingerprint or "",
            approved_by="human",
        )
        blocked = await agnes.execute_skill(
            {
                "id": "hands.code_patch",
                "executor": "sandbox",
                "inputs": {"patch": patch},
                "allowlist_paths": ["**"],
                "granted_capabilities": ["code_write", "patch"],
                "execution_id": f"bad-{index}",
            },
            goal="bad patch",
            correlation_id=f"bad-corr-{index}",
            workspace_id=f"bad-ws-{index}",
            baseline_commit=BASELINE,
            approval_id=f"bad-approval-{index}",
            idempotency_key=f"bad-idem-{index}",
        )
        assert blocked.status is ExecutionStatus.FAILED
        assert blocked.error and blocked.error.startswith("sandbox_guard:")


@pytest.mark.asyncio
async def test_sqlite_idempotency_survives_new_store_instance(tmp_path: Path):
    path = tmp_path / "idem.sqlite3"
    first = SQLiteIdempotencyStore(path)
    claimed, _ = await first.claim("k", "manifest-1")
    assert claimed is True
    await first.complete("k", success=True, result={"ok": True})
    second = SQLiteIdempotencyStore(path)
    claimed_again, record = await second.claim("k", "manifest-1")
    assert claimed_again is False
    assert record is not None
    assert record.result == {"ok": True}


def test_phase2_status_does_not_claim_production_safe(tmp_path: Path):
    agnes = _agnes(tmp_path)
    status = agnes.dispatcher.status()
    assert status["sandbox_executor_enabled"] is True
    assert status["workspace_is_sandbox"] is True
    assert status["idempotency"]["durable"] is True
    assert status["idempotency"]["production_safe"] is False
    assert "R12" in status["production_execution"]


@pytest.mark.asyncio
async def test_system_mounts_are_read_only_and_output_is_bounded(tmp_path: Path):
    work = tmp_path / "work-ro"
    work.mkdir()
    runner = LinuxNamespaceRunner(
        SandboxPolicy(
            base_dir=tmp_path / "runtime-ro",
            repository_root=REPO,
            max_output_bytes=1024,
        )
    )
    ro = await runner.run(
        workspace=work,
        execution_id="readonly",
        command=[
            "python",
            "-c",
            "import pathlib; p=pathlib.Path('/usr/agnes-phase2-write');\n"
            "\ntry: p.write_text('x'); print('write-open')\n"
            "except Exception as e: print('write-blocked', type(e).__name__)",
        ],
        timeout_seconds=10,
    )
    assert ro.returncode == 0
    assert "write-blocked" in ro.stdout
    assert "write-open" not in ro.stdout

    flood = await runner.run(
        workspace=work,
        execution_id="flood",
        command=["python", "-c", "print('x'*100000)"],
        timeout_seconds=10,
    )
    assert flood.output_limited is True
    assert len(flood.stdout.encode()) <= 1024


def test_command_guard_denies_shell_and_network_git():
    from creator_app.agnes.execution.sandbox import CommandGuard

    with pytest.raises(SandboxViolation):
        CommandGuard.validate(["bash", "-lc", "echo unsafe"])
    with pytest.raises(SandboxViolation):
        CommandGuard.validate(["git", "push", "origin", "main"])


@pytest.mark.asyncio
async def test_api_phase2_approval_then_execute(tmp_path: Path):
    from fastapi.testclient import TestClient

    from creator_app.api import create_app
    from creator_app.config import Settings

    settings = Settings(
        mock_ai=True,
        access_token="test-access-token",
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "ledger.jsonl",
        agnes_sandbox_enabled=True,
        agnes_sandbox_root=tmp_path / "api-sandbox",
        agnes_sandbox_repository_root=REPO,
    )
    payload = {
        "skill_id": "hands.code_patch",
        "goal": "api sandbox patch",
        "executor": "sandbox",
        "inputs": {
            "patch": "--- /dev/null\n+++ b/api_phase2_probe.py\n@@ -0,0 +1 @@\n+print('api-ok')\n"
        },
        "correlation_id": "api-corr",
        "workspace_id": "api-ws",
        "baseline_commit": BASELINE,
        "idempotency_key": "api-idem",
        "allowlist_paths": ["api_phase2_probe.py"],
        "granted_capabilities": ["code_write", "patch"],
    }
    app = create_app(settings)
    app.state.agnes.execution_context_factory = make_test_omni_context
    with TestClient(app) as client:
        client.headers.update({"Authorization": "Bearer test-access-token"})
        first = client.post("/api/agnes/execute", json=payload)
        assert first.status_code == 200
        waiting = first.json()
        assert waiting["status"] == "waiting_approval"
        fingerprint = waiting["approval_fingerprint"]
        approved = client.post(
            "/api/agnes/approvals",
            json={
                "approval_id": "api-approval",
                "fingerprint": fingerprint,
                "approved_by": "tester",
                "ttl_seconds": 300,
            },
        )
        assert approved.status_code == 200
        payload["approval_id"] = "api-approval"
        second = client.post("/api/agnes/execute", json=payload)
        assert second.status_code == 200
        assert second.json()["status"] == "succeeded"
        status = client.get("/api/agnes/execution/status").json()
        assert status["sandbox_executor_enabled"] is True
        assert status["idempotency"]["durable"] is True


def test_workspace_requires_full_commit_and_rejects_symlinks(tmp_path: Path):
    from creator_app.agnes.execution.sandbox import SandboxWorkspaceManager

    policy = SandboxPolicy(base_dir=tmp_path / "sandbox-ws", repository_root=REPO)
    manager = SandboxWorkspaceManager(policy)
    with pytest.raises(SandboxViolation):
        manager.open("ws-bad-commit", "--output=/tmp/x")

    workspace = manager.open("ws-symlink", BASELINE)
    (workspace.path / "allowed-link").symlink_to("/etc/passwd")
    with pytest.raises(SandboxViolation):
        manager.validate_diff(workspace, ("allowed-link",))
