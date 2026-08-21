from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SandboxPlatformProfile:
    name: str
    executable_roots: tuple[Path, ...]
    virtual_root_map: tuple[tuple[Path, str], ...] = ()
    namespace_expected: bool = True

    def allows_executable(self, executable: str | Path) -> bool:
        resolved = Path(executable).resolve()
        for root in self.executable_roots:
            canonical = root.resolve()
            try:
                resolved.relative_to(canonical)
                return True
            except ValueError:
                continue
        return False


def detect_platform_profile(
    environment: dict[str, str] | None = None,
) -> SandboxPlatformProfile:
    env = environment or dict(os.environ)
    prefix = str(env.get("PREFIX", "")).strip()
    if prefix:
        canonical = Path(prefix).resolve()
        expected = Path("/data/data/com.termux/files/usr")
        if canonical == expected:
            return SandboxPlatformProfile(
                name="termux_android",
                executable_roots=(canonical / "bin", canonical / "libexec"),
                virtual_root_map=((canonical, "/opt/ck-termux-root"),),
                namespace_expected=False,
            )
    return SandboxPlatformProfile(
        name="linux",
        executable_roots=(Path("/usr"), Path("/bin"), Path("/opt"), Path("/usr/local")),
        namespace_expected=True,
    )
