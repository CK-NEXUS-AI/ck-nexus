from __future__ import annotations

import contextlib
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
    """cgroup v2 manager for an explicitly delegated subtree.

    Health checks are conservative: a unified cgroup v2 mount is not enough. The
    configured root must be writable and expose the CPU, memory and PIDs
    controllers before CK-NEXUS considers enforcement ready.
    """

    REQUIRED_CONTROLLERS = frozenset({"cpu", "memory", "pids"})

    def __init__(
        self, root: Path = Path("/sys/fs/cgroup"), group_prefix: str = "cknexus-agnes"
    ) -> None:
        self.root = root
        self.group_prefix = group_prefix

    def health(self) -> dict[str, object]:
        controllers_file = self.root / "cgroup.controllers"
        unified = controllers_file.exists()
        controllers: set[str] = set()
        if unified:
            try:
                controllers = set(controllers_file.read_text(encoding="utf-8").split())
            except OSError:
                controllers = set()
        writable = self.root.is_dir() and os.access(self.root, os.W_OK)
        missing = sorted(self.REQUIRED_CONTROLLERS - controllers)
        return {
            "unified_v2": unified,
            "delegated_writable": writable,
            "controllers": sorted(controllers),
            "required_controllers": sorted(self.REQUIRED_CONTROLLERS),
            "missing_controllers": missing,
            "ready": unified and writable and not missing,
            "root": str(self.root),
        }

    def create(self, execution_id: str, limits: CgroupLimits) -> Path:
        if not self.health()["ready"]:
            raise RuntimeError("cgroup_v2_not_delegated_writable")
        safe = "".join(ch for ch in execution_id if ch.isalnum() or ch in "-_")[:96]
        if not safe:
            raise ValueError("cgroup_execution_id_required")
        path = self.root / f"{self.group_prefix}-{safe}"
        path.mkdir(exist_ok=False)
        try:
            (path / "cpu.max").write_text(f"{limits.cpu_quota_us} {limits.cpu_period_us}")
            (path / "memory.max").write_text(str(limits.memory_max_bytes))
            (path / "pids.max").write_text(str(limits.pids_max))
            if limits.io_max and (path / "io.max").exists():
                (path / "io.max").write_text(limits.io_max)
        except Exception:
            self.cleanup(path)
            raise
        return path

    @staticmethod
    def attach(path: Path, pid: int) -> None:
        if pid <= 0:
            raise ValueError("cgroup_pid_must_be_positive")
        (path / "cgroup.procs").write_text(str(pid))

    @staticmethod
    def cleanup(path: Path) -> None:
        with contextlib.suppress(OSError):
            path.rmdir()
