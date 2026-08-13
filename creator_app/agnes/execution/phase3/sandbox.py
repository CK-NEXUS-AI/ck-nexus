from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..sandbox.runner import LinuxNamespaceRunner
from .hardening import CgroupLimits, CgroupV2Manager

_SECCOMP_C = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DENY_NR(nr) \
    BPF_JUMP(BPF_JMP+BPF_JEQ+BPF_K, (nr), 0, 1), \
    BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_ERRNO | (EPERM & SECCOMP_RET_DATA))

int main(int argc, char **argv) {
    if (argc < 2) return 64;
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) { perror("no_new_privs"); return 65; }
    struct sock_filter filter[] = {
        BPF_STMT(BPF_LD+BPF_W+BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP+BPF_JEQ+BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD+BPF_W+BPF_ABS, offsetof(struct seccomp_data, nr)),
#ifdef __NR_mount
        DENY_NR(__NR_mount),
#endif
#ifdef __NR_umount2
        DENY_NR(__NR_umount2),
#endif
#ifdef __NR_pivot_root
        DENY_NR(__NR_pivot_root),
#endif
#ifdef __NR_ptrace
        DENY_NR(__NR_ptrace),
#endif
#ifdef __NR_bpf
        DENY_NR(__NR_bpf),
#endif
#ifdef __NR_perf_event_open
        DENY_NR(__NR_perf_event_open),
#endif
#ifdef __NR_kexec_load
        DENY_NR(__NR_kexec_load),
#endif
#ifdef __NR_kexec_file_load
        DENY_NR(__NR_kexec_file_load),
#endif
#ifdef __NR_reboot
        DENY_NR(__NR_reboot),
#endif
#ifdef __NR_init_module
        DENY_NR(__NR_init_module),
#endif
#ifdef __NR_finit_module
        DENY_NR(__NR_finit_module),
#endif
#ifdef __NR_delete_module
        DENY_NR(__NR_delete_module),
#endif
#ifdef __NR_keyctl
        DENY_NR(__NR_keyctl),
#endif
#ifdef __NR_add_key
        DENY_NR(__NR_add_key),
#endif
#ifdef __NR_request_key
        DENY_NR(__NR_request_key),
#endif
#ifdef __NR_unshare
        DENY_NR(__NR_unshare),
#endif
#ifdef __NR_setns
        DENY_NR(__NR_setns),
#endif
        BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_ALLOW),
    };
    struct sock_fprog prog = { .len = (unsigned short)(sizeof(filter)/sizeof(filter[0])), .filter = filter };
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog)) { perror("seccomp"); return 66; }
    execvp(argv[1], &argv[1]);
    perror("execvp");
    return 127;
}
'''


class HardenedLinuxNamespaceRunner(LinuxNamespaceRunner):
    """Phase-3 namespace/chroot runner with no_new_privs, capability drop and seccomp.

    cgroup v2 is detected independently. The current runner only declares the backend
    fully production-safe when a delegated writable cgroup v2 tree is available.
    """

    backend_name = "linux_namespace_chroot_seccomp"

    def __init__(self, policy, *, cgroups: CgroupV2Manager | None = None) -> None:
        super().__init__(policy)
        self.cgroups = cgroups or CgroupV2Manager()
        self.launcher = self._build_launcher()
        self._active_cgroups: dict[str, Path] = {}
        self.production_safe = bool(self.cgroups.health().get("ready"))

    def _build_launcher(self) -> Path:
        bindir = self.policy.base_dir / "bin"
        bindir.mkdir(parents=True, exist_ok=True, mode=0o700)
        source = bindir / "agnes_seccomp.c"
        binary = bindir / "agnes-seccomp"
        source.write_text(_SECCOMP_C, encoding="utf-8")
        gcc = shutil.which("gcc")
        if not gcc:
            raise RuntimeError("gcc_required_to_build_seccomp_launcher")
        proc = subprocess.run(
            [gcc, "-O2", "-Wall", "-Wextra", str(source), "-o", str(binary)],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError("seccomp_launcher_build_failed:" + proc.stderr.decode(errors="replace")[:1000])
        binary.chmod(0o500)
        return binary

    def _launcher_path(self) -> str:
        return str(self.launcher)

    async def _after_process_start(self, pid: int, execution_id: str) -> None:
        if not self.cgroups.health().get("ready"):
            return
        path = self.cgroups.create(
            execution_id,
            CgroupLimits(
                cpu_quota_us=max(1_000, min(100_000, self.policy.cpu_seconds * 1_000)),
                memory_max_bytes=self.policy.memory_bytes,
                pids_max=self.policy.max_processes,
            ),
        )
        self.cgroups.attach(path, pid)
        self._active_cgroups[execution_id] = path

    async def _after_process_finish(self, execution_id: str) -> None:
        path = self._active_cgroups.pop(execution_id, None)
        if path is not None:
            self.cgroups.cleanup(path)

    async def health(self) -> dict[str, object]:
        base = await super().health()
        cgroup = self.cgroups.health()
        return {
            **base,
            "backend": self.backend_name,
            "seccomp": "enabled_deny_dangerous_syscalls",
            "no_new_privs": True,
            "capabilities": "bounding_inheritable_ambient_dropped",
            "cgroup_v2": cgroup,
            "production_safe": bool(base.get("ready")) and bool(cgroup.get("ready")),
        }
