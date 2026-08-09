from __future__ import annotations

from pathlib import Path

import pytest

from creator_app.agnes_runtime import AgnesNervousSystem
from creator_app.agnes.execution.phase3.hardening import CgroupV2Manager

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "creator_app" / "skills" / "agnes" / "SKILL.md"


def test_cgroup_health_requires_cpu_memory_and_pids(tmp_path: Path) -> None:
    (tmp_path / "cgroup.controllers").write_text("cpu memory\n", encoding="utf-8")
    health = CgroupV2Manager(tmp_path).health()
    assert health["unified_v2"] is True
    assert health["delegated_writable"] is True
    assert health["ready"] is False
    assert health["missing_controllers"] == ["pids"]


def test_cgroup_health_ready_for_delegated_required_controllers(tmp_path: Path) -> None:
    (tmp_path / "cgroup.controllers").write_text("io memory pids cpu\n", encoding="utf-8")
    health = CgroupV2Manager(tmp_path).health()
    assert health["ready"] is True
    assert health["missing_controllers"] == []


def test_staging_phase3_fails_closed_when_cgroup_not_delegated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import types, sys
    fake_redis = types.ModuleType("redis")
    fake_asyncio = types.ModuleType("redis.asyncio")
    class FakeRedisClient:
        @classmethod
        def from_url(cls, *args, **kwargs):
            return object()
    fake_asyncio.Redis = FakeRedisClient
    fake_redis.asyncio = fake_asyncio
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    monkeypatch.setitem(sys.modules, "redis.asyncio", fake_asyncio)
    cgroup_root = tmp_path / "not-delegated"
    cgroup_root.mkdir()
    with pytest.raises(RuntimeError, match="cgroup_v2_enforcement_required"):
        AgnesNervousSystem(
            skill_file=SKILLS,
            ledger_path=tmp_path / "ledger.jsonl",
            sandbox_enabled=True,
            sandbox_root=tmp_path / "sandbox",
            sandbox_repository_root=ROOT,
            phase3_enabled=True,
            environment="staging",
            phase3_redis_url="redis://127.0.0.1:6379/0",
            phase3_cgroup_root=cgroup_root,
        )


def test_development_phase3_keeps_truthful_non_production_safe_status(tmp_path: Path) -> None:
    cgroup_root = tmp_path / "not-delegated"
    cgroup_root.mkdir()
    from creator_app.agnes.execution.phase3.sandbox import HardenedLinuxNamespaceRunner
    from creator_app.agnes.execution.sandbox import SandboxPolicy
    runner = HardenedLinuxNamespaceRunner(
        SandboxPolicy(base_dir=tmp_path / "sandbox", repository_root=ROOT),
        cgroups=CgroupV2Manager(cgroup_root),
    )
    assert runner.production_safe is False
