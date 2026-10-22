from __future__ import annotations

import errno
from pathlib import Path

import pytest

from creator_app.agnes.execution.phase3 import PipelineHandle, PipelineState, RedisIdempotencyStore
from creator_app.agnes.execution.phase3.hardening import CgroupV2Manager
from creator_app.agnes.execution.phase3.sandbox import HardenedLinuxNamespaceRunner
from creator_app.agnes.execution.sandbox import SandboxPolicy, SandboxWorkspaceManager
from creator_app.agnes_runtime import AgnesNervousSystem
from tests.omni_context_factory import make_test_omni_context

BASELINE = "dce9e0f30e4e17d43c794c7f8ddb1e7d6e85f17e"
ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "creator_app" / "skills" / "agnes" / "SKILL.md"


def _agnes(tmp_path: Path) -> AgnesNervousSystem:
    return AgnesNervousSystem(
        skill_file=SKILLS,
        ledger_path=tmp_path / "ledger.jsonl",
        sandbox_enabled=True,
        sandbox_root=tmp_path / "sandbox",
        sandbox_repository_root=ROOT,
        phase3_enabled=True,
        execution_context_factory=make_test_omni_context,
    )


@pytest.mark.asyncio
async def test_hardened_runner_enables_no_new_privs_and_seccomp(tmp_path: Path):
    policy = SandboxPolicy(base_dir=tmp_path / "s", repository_root=ROOT)
    manager = SandboxWorkspaceManager(policy)
    ws = manager.open("seccomp-ws", BASELINE)
    runner = HardenedLinuxNamespaceRunner(policy)
    health = await runner.health()
    assert health["ready"] is True
    assert health["seccomp"] == "enabled_deny_dangerous_syscalls"
    result = await runner.run(
        workspace=ws.path,
        execution_id="seccomp-test",
        command=[
            "python",
            "-c",
            "import ctypes,errno; l=ctypes.CDLL(None,use_errno=True); "
            "print('nnp',l.prctl(39,0,0,0,0)); "
            "r=l.mount(b'none',b'/tmp',b'tmpfs',0,b''); print('mount',r,ctypes.get_errno())",
        ],
        timeout_seconds=30,
    )
    assert result.returncode == 0
    assert "nnp 1" in result.stdout
    assert f"mount -1 {errno.EPERM}" in result.stdout


def test_cgroup_v2_doctor_is_truthful():
    health = CgroupV2Manager().health()
    assert health["unified_v2"] is True
    # This CI/sandbox mounts cgroup2 read-only, so Phase 3 must not fake enforcement.
    assert health["ready"] is health["delegated_writable"]


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, nx=False, xx=False, ex=None):
        if nx and key in self.data:
            return False
        if xx and key not in self.data:
            return False
        self.data[key] = value
        return True

    async def get(self, key):
        return self.data.get(key)


@pytest.mark.asyncio
async def test_redis_idempotency_coordinates_two_dispatcher_instances():
    backend = FakeRedis()
    a = RedisIdempotencyStore(backend)
    b = RedisIdempotencyStore(backend)
    claimed_a, _ = await a.claim("tenant:skill:key", "manifest-a")
    claimed_b, record = await b.claim("tenant:skill:key", "manifest-a")
    assert claimed_a is True
    assert claimed_b is False
    assert record and record.manifest_hash == "manifest-a"
    await a.complete("tenant:skill:key", success=True, result={"ok": True})
    _, replay = await b.claim("tenant:skill:key", "manifest-a")
    assert replay and replay.result == {"ok": True}


@pytest.mark.asyncio
async def test_autonomous_pipeline_stops_at_candidate_and_can_discard(tmp_path: Path):
    agnes = _agnes(tmp_path)
    assert agnes.dev_controller is not None
    patch = (
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -1,3 +1,4 @@\n"
        " # CK-NEXUS Creator Edition\n"
        "+Phase3 candidate test.\n"
        "\n"
        " ระบบ AI แบบเมนูสำหรับครีเอเตอร์: เลือก Agent, ใส่ Creative Brief "
        "สั้น ๆ, สร้างผลงาน "
        "และเก็บประวัติไว้ใน SQLite บนเครื่องของผู้ใช้\n"
    )
    from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest

    request = SkillExecutionRequest(
        execution_id="p3exec",
        correlation_id="p3corr",
        skill_id="hands.code_patch",
        skill_version=agnes.registry.get("hands.code_patch").version,
        executor=ExecutorType.SANDBOX,
        goal="phase3 pipeline",
        inputs={
            "patch": patch,
            "test_command": ["python", "-m", "compileall", "-q", "."],
            "scan_command": ["python", "-c", "print('security-scan:PASS')"],
        },
        workspace_id="p3ws",
        baseline_commit=BASELINE,
        idempotency_key="p3-idem",
        allowlist_paths=("README.md",),
        granted_capabilities=("code_write", "patch"),
    )
    handle = await agnes.dev_controller.start_pipeline(request)
    pending = await agnes.dev_controller.run_to_candidate(handle)
    assert pending.state is PipelineState.PENDING_APPROVAL
    assert pending.approval_fingerprint
    agnes.approvals.grant(
        approval_id="p3-approval",
        fingerprint=pending.approval_fingerprint,
        approved_by="human",
    )
    # Approval ID is part of the immutable request, so create a replacement pipeline
    # whose approval is bound before execution.
    request2 = SkillExecutionRequest(
        execution_id="p3exec2",
        correlation_id="p3corr2",
        skill_id=request.skill_id,
        skill_version=request.skill_version,
        executor=request.executor,
        goal=request.goal,
        inputs=request.inputs,
        workspace_id="p3ws2",
        baseline_commit=BASELINE,
        approval_id=None,
        idempotency_key="p3-idem2",
        allowlist_paths=request.allowlist_paths,
        granted_capabilities=request.granted_capabilities,
    )
    handle2 = await agnes.dev_controller.start_pipeline(request2)
    pending2 = await agnes.dev_controller.run_to_candidate(handle2)
    agnes.approvals.grant(
        approval_id="p3-approval2",
        fingerprint=pending2.approval_fingerprint or "",
        approved_by="human",
    )
    # Controller request is immutable; bind approval by replacing the stored request
    # with an approved clone.
    request3 = SkillExecutionRequest(
        execution_id=request2.execution_id,
        correlation_id=request2.correlation_id,
        skill_id=request2.skill_id,
        skill_version=request2.skill_version,
        executor=request2.executor,
        goal=request2.goal,
        inputs=request2.inputs,
        workspace_id=request2.workspace_id,
        baseline_commit=request2.baseline_commit,
        approval_id="p3-approval2",
        idempotency_key=request2.idempotency_key,
        allowlist_paths=request2.allowlist_paths,
        granted_capabilities=request2.granted_capabilities,
    )
    # Fingerprint includes approval-independent immutable work identity, so approved clone matches.
    agnes.dev_controller._requests[handle2.pipeline_id] = request3
    final = await agnes.dev_controller.run_to_candidate(
        PipelineHandle(handle2.pipeline_id, request3.execution_id)
    )
    assert final.state is PipelineState.CANDIDATE_READY
    candidate = await agnes.dev_controller.collect_candidate(handle2.pipeline_id)
    assert candidate.requires_merge_approval is True
    assert "Phase3 candidate test" in candidate.diff
    assert candidate.result_commit is None
    await agnes.dev_controller.discard(handle2.pipeline_id, "test cleanup")
    discarded = await agnes.dev_controller.get_status(handle2.pipeline_id)
    assert discarded.state is PipelineState.DISCARDED


@pytest.mark.asyncio
async def test_pipeline_failure_rolls_back_workspace(tmp_path: Path):
    agnes = _agnes(tmp_path)
    patch = (
        "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-# CK-NEXUS Creator Edition\n+# BROKEN\n"
    )
    from creator_app.agnes.execution.request import ExecutorType, SkillExecutionRequest

    req = SkillExecutionRequest(
        execution_id="fail-exec",
        correlation_id="fail-corr",
        skill_id="hands.code_patch",
        skill_version=agnes.registry.get("hands.code_patch").version,
        executor=ExecutorType.SANDBOX,
        goal="failure rollback",
        inputs={"patch": patch, "test_command": ["python", "-c", "raise SystemExit(7)"]},
        workspace_id="fail-ws",
        baseline_commit=BASELINE,
        idempotency_key="fail-idem",
        allowlist_paths=("README.md",),
        granted_capabilities=("code_write", "patch"),
    )
    h = await agnes.dev_controller.start_pipeline(req)
    p = await agnes.dev_controller.run_to_candidate(h)
    agnes.approvals.grant(
        approval_id="fail-a", fingerprint=p.approval_fingerprint or "", approved_by="human"
    )
    approved = SkillExecutionRequest(
        execution_id=req.execution_id,
        correlation_id=req.correlation_id,
        skill_id=req.skill_id,
        skill_version=req.skill_version,
        executor=req.executor,
        goal=req.goal,
        inputs=req.inputs,
        workspace_id=req.workspace_id,
        baseline_commit=req.baseline_commit,
        approval_id="fail-a",
        idempotency_key=req.idempotency_key,
        allowlist_paths=req.allowlist_paths,
        granted_capabilities=req.granted_capabilities,
    )
    agnes.dev_controller._requests[h.pipeline_id] = approved
    final = await agnes.dev_controller.run_to_candidate(
        PipelineHandle(h.pipeline_id, approved.execution_id)
    )
    assert final.state is PipelineState.ROLLED_BACK
    assert not (tmp_path / "sandbox" / "workspaces" / "fail-ws").exists()


def test_phase3_api_pending_approval_then_advance_to_candidate(tmp_path: Path):
    from fastapi.testclient import TestClient

    from creator_app.api import create_app
    from creator_app.config import Settings

    settings = Settings(
        mock_ai=True,
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "ledger.jsonl",
        agnes_sandbox_enabled=True,
        agnes_phase3_enabled=True,
        agnes_sandbox_root=tmp_path / "sandbox",
        agnes_sandbox_repository_root=ROOT,
    )
    patch = (
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -1,3 +1,4 @@\n"
        " # CK-NEXUS Creator Edition\n"
        "+API Phase3 candidate.\n"
        " \n"
        " ระบบ AI แบบเมนูสำหรับครีเอเตอร์: เลือก Agent, ใส่ Creative Brief "
        "สั้น ๆ, สร้างผลงาน "
        "และเก็บประวัติไว้ใน SQLite บนเครื่องของผู้ใช้\n"
    )
    app = create_app(settings)
    app.state.agnes.execution_context_factory = make_test_omni_context
    with TestClient(app) as client:
        start = client.post(
            "/api/agnes/pipeline/start",
            json={
                "goal": "phase3 api",
                "patch": patch,
                "baseline_commit": BASELINE,
                "idempotency_key": "api-p3",
                "allowlist_paths": ["README.md"],
            },
        )
        assert start.status_code == 200
        body = start.json()
        assert body["state"] == "pending_approval"
        fp = body["approval_fingerprint"]
        pipeline_id = body["pipeline_id"]
        approved = client.post(
            "/api/agnes/approvals",
            json={"approval_id": "api-p3-approval", "fingerprint": fp, "approved_by": "human"},
        )
        assert approved.status_code == 200
        advanced = client.post(f"/api/agnes/pipeline/{pipeline_id}/advance")
        assert advanced.status_code == 200
        assert advanced.json()["state"] == "candidate_ready"
        status = client.get(f"/api/agnes/pipeline/{pipeline_id}")
        assert status.status_code == 200
        assert status.json()["candidate"]["requires_merge_approval"] is True
