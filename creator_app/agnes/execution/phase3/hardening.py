from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CgroupLimits:
    cpu_quota_us: int = 50_000
    cpu_period_us: int = 100_000
    memory_max_bytes: int = 768 * 1024 * 1024
    pids_max: int = 96
    io_max: str | None = None


class CgroupV2Manager:
    """cgroup v2 manager. Fails closed when the delegated cgroup tree is not writable."""

    def __init__(self, root: Path = Path("/sys/fs/cgroup"), group_prefix: str = "cknexus-agnes") -> None:
        self.root = root
        self.group_prefix = group_prefix

    def health(self) -> dict[str, object]:
        unified = (self.root / "cgroup.controllers").exists()
        writable = os.access(self.root, os.W_OK)
        return {
            "unified_v2": unified,
            "delegated_writable": writable,
            "ready": unified and writable,
            "root": str(self.root),
        }

    def create(self, execution_id: str, limits: CgroupLimits) -> Path:
        if not self.health()["ready"]:
            raise RuntimeError("cgroup_v2_not_delegated_writable")
        safe = "".join(ch for ch in execution_id if ch.isalnum() or ch in "-_")[:96]
        path = self.root / f"{self.group_prefix}-{safe}"
        path.mkdir(exist_ok=False)
        (path / "cpu.max").write_text(f"{limits.cpu_quota_us} {limits.cpu_period_us}")
        (path / "memory.max").write_text(str(limits.memory_max_bytes))
        (path / "pids.max").write_text(str(limits.pids_max))
        if limits.io_max and (path / "io.max").exists():
            (path / "io.max").write_text(limits.io_max)
        return path

    @staticmethod
    def attach(path: Path, pid: int) -> None:
        (path / "cgroup.procs").write_text(str(pid))

    @staticmethod
    def cleanup(path: Path) -> None:
        try:
            path.rmdir()
        except OSError:
            pass
