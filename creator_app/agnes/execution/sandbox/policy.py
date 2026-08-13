from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    base_dir: Path
    repository_root: Path
    network_mode: str = "deny"
    cpu_seconds: int = 60
    memory_bytes: int = 768 * 1024 * 1024
    max_processes: int = 96
    max_file_bytes: int = 128 * 1024 * 1024
    max_open_files: int = 256
    max_output_bytes: int = 2 * 1024 * 1024
    kill_grace_seconds: float = 1.0
    require_namespace: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_dir", self.base_dir.resolve())
        object.__setattr__(self, "repository_root", self.repository_root.resolve())
        if self.network_mode != "deny":
            raise ValueError("Phase 2 local sandbox only supports network_mode=deny")
        if (
            min(
                self.cpu_seconds,
                self.memory_bytes,
                self.max_processes,
                self.max_file_bytes,
                self.max_open_files,
                self.max_output_bytes,
            )
            <= 0
        ):
            raise ValueError("sandbox resource limits must be positive")
