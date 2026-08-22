from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import signal
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    import resource
except ImportError:  # Windows: Linux sandbox remains unavailable/fail-closed.
    resource = None  # type: ignore[assignment]

from .guards import CommandGuard, SandboxViolation
from .platform import SandboxPlatformProfile, detect_platform_profile
from .policy import SandboxPolicy


@dataclass(frozen=True, slots=True)
class SandboxCommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    output_limited: bool = False


_SETUP_SCRIPT = r"""
set -euo pipefail
ROOT="$1"
WORK="$2"
LAUNCHER="$3"
shift 3
mount --make-rprivate /
for d in usr bin lib lib64 opt; do
  if [ -e "/$d" ]; then
    mkdir -p "$ROOT/$d"
    mount --bind "/$d" "$ROOT/$d"
    mount -o remount,bind,ro "$ROOT/$d"
  fi
done
mkdir -p "$ROOT/workspace" "$ROOT/tmp" "$ROOT/dev" "$ROOT/opt"
mount --bind "$WORK" "$ROOT/workspace"
mount -t tmpfs -o nodev,nosuid,noexec,size=64m tmpfs "$ROOT/tmp"
for dev in null zero random urandom; do
  if [ -e "/dev/$dev" ]; then
    touch "$ROOT/dev/$dev"
    mount --bind "/dev/$dev" "$ROOT/dev/$dev"
    mount -o remount,bind,ro "$ROOT/dev/$dev"
  fi
done
if [ -n "$LAUNCHER" ]; then
  touch "$ROOT/agnes-seccomp"
  mount --bind "$LAUNCHER" "$ROOT/agnes-seccomp"
  mount -o remount,bind,ro "$ROOT/agnes-seccomp"
  exec chroot "$ROOT" /usr/bin/env -i \
    PATH=/opt/pyvenv/bin:/usr/local/bin:/usr/bin:/bin \
    HOME=/tmp TMPDIR=/tmp PYTHONPATH=/workspace CKNEXUS_SANDBOX=hardened_linux_namespace \
    /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all \
    /bin/bash -c 'cd /workspace && exec /agnes-seccomp "$@"' _ "$@"
fi
exec chroot "$ROOT" /usr/bin/env -i \
  PATH=/opt/pyvenv/bin:/usr/local/bin:/usr/bin:/bin \
  HOME=/tmp \
  TMPDIR=/tmp \
  PYTHONPATH=/workspace \
  CKNEXUS_SANDBOX=linux_namespace \
  /bin/bash -c 'cd /workspace && exec "$@"' _ "$@"
"""


class LinuxNamespaceRunner:
    """Linux user/mount/PID/network namespace + chroot development sandbox.

    It provides real filesystem-root and network namespace separation on supported
    Linux hosts, but remains `production_safe=False` until a hardened backend adds
    seccomp/cgroup enforcement and passes staging evidence.
    """

    backend_name = "linux_namespace_chroot"
    production_safe = False

    def __init__(
        self,
        policy: SandboxPolicy,
        *,
        platform_profile: SandboxPlatformProfile | None = None,
    ) -> None:
        self.policy = policy
        self.platform_profile = platform_profile or detect_platform_profile()
        self.unshare = shutil.which("unshare")
        if self.policy.require_namespace and not self.unshare:
            raise RuntimeError("unshare_not_available")

    async def health(self) -> dict[str, object]:
        if not self.unshare:
            return {
                "ready": False,
                "backend": self.backend_name,
                "platform": self.platform_profile.name,
                "reason": "unshare_not_available",
            }
        proc = await asyncio.create_subprocess_exec(
            self.unshare,
            "-Urmpn",
            "--fork",
            "/bin/true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        return {
            "ready": proc.returncode == 0,
            "backend": self.backend_name,
            "platform": self.platform_profile.name,
            "virtual_root_map": [
                (str(src), dst) for src, dst in self.platform_profile.virtual_root_map
            ],
            "network": "isolated_namespace",
            "filesystem": "chroot_with_read_only_system_binds",
            "production_safe": self.production_safe,
            "reason": (
                None if proc.returncode == 0 else stderr.decode(errors="replace")[:1000]
            ),
        }

    def _resolve_executable(self, command: tuple[str, ...]) -> tuple[str, ...]:
        executable = shutil.which(command[0])
        if executable is None:
            raise SandboxViolation(f"command_unavailable:{command[0]}")
        if not self.platform_profile.allows_executable(executable):
            raise SandboxViolation("executable_outside_readonly_system_roots")
        return (str(Path(executable).resolve()), *command[1:])

    def _launcher_path(self) -> str:
        return ""

    async def _after_process_start(self, pid: int, execution_id: str) -> None:
        return None

    async def _after_process_finish(self, execution_id: str) -> None:
        return None

    def _limits(self) -> None:
        if resource is None:
            raise RuntimeError("posix_resource_limits_unavailable")
        resource.setrlimit(
            resource.RLIMIT_CPU, (self.policy.cpu_seconds, self.policy.cpu_seconds + 1)
        )
        resource.setrlimit(
            resource.RLIMIT_AS, (self.policy.memory_bytes, self.policy.memory_bytes)
        )
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (self.policy.max_processes, self.policy.max_processes),
        )
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (self.policy.max_file_bytes, self.policy.max_file_bytes),
        )
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (self.policy.max_open_files, self.policy.max_open_files),
        )

    async def run(
        self,
        *,
        workspace: Path,
        execution_id: str,
        command: list[str] | tuple[str, ...],
        timeout_seconds: int,
    ) -> SandboxCommandResult:
        validated = CommandGuard.validate(command)
        resolved = self._resolve_executable(validated)
        if not workspace.is_dir():
            raise SandboxViolation("workspace_missing")
        runtime_parent = self.policy.base_dir / "runtime"
        runtime_parent.mkdir(parents=True, exist_ok=True)
        rootfs = (
            Path(tempfile.mkdtemp(prefix=f"{execution_id}-", dir=runtime_parent))
            / "root"
        )
        rootfs.mkdir(parents=True, exist_ok=True)
        args = [
            self.unshare or "unshare",
            "-Urmpn",
            "--fork",
            "/bin/bash",
            "-c",
            _SETUP_SCRIPT,
            "_",
            str(rootfs),
            str(workspace.resolve()),
            self._launcher_path(),
            *resolved,
        ]
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            preexec_fn=self._limits,
        )
        await self._after_process_start(proc.pid, execution_id)
        output_limited = False

        async def read_limited(stream: asyncio.StreamReader | None) -> bytes:
            nonlocal output_limited
            if stream is None:
                return b""
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > self.policy.max_output_bytes:
                    output_limited = True
                    remaining = max(
                        0, self.policy.max_output_bytes - (total - len(chunk))
                    )
                    if remaining:
                        chunks.append(chunk[:remaining])
                    self._kill_group(proc.pid, signal.SIGTERM)
                    break
                chunks.append(chunk)
            return b"".join(chunks)

        stdout_task = asyncio.create_task(read_limited(proc.stdout))
        stderr_task = asyncio.create_task(read_limited(proc.stderr))
        timed_out = False
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_seconds)
        except TimeoutError:
            timed_out = True
            self._kill_group(proc.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(
                    proc.wait(), timeout=self.policy.kill_grace_seconds
                )
            except TimeoutError:
                self._kill_group(proc.pid, signal.SIGKILL)
                await proc.wait()
        finally:
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
            await self._after_process_finish(execution_id)
            shutil.rmtree(rootfs.parent, ignore_errors=True)

        return SandboxCommandResult(
            returncode=(
                proc.returncode if proc.returncode is not None else -signal.SIGKILL
            ),
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            timed_out=timed_out,
            output_limited=output_limited,
        )

    @staticmethod
    def _kill_group(pid: int, sig: signal.Signals) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pid, sig)
