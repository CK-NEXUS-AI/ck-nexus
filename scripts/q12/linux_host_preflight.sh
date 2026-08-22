#!/usr/bin/env bash
set -euo pipefail

fail=0
check() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "$name"
  else
    printf 'FAIL  %s\n' "$name"
    fail=1
  fi
}

echo "CK-NEXUS Q12 Linux Host Preflight"
echo "kernel=$(uname -srmo)"
echo "uid=$(id -u) user=$(id -un)"
echo "cgroup_fs=$(stat -fc %T /sys/fs/cgroup 2>/dev/null || echo unavailable)"

check "systemd available" test -d /run/systemd/system
check "cgroup v2 mounted" test "$(stat -fc %T /sys/fs/cgroup 2>/dev/null || true)" = "cgroup2fs"
check "cgroup controllers file" test -r /sys/fs/cgroup/cgroup.controllers
check "cpu controller" grep -qw cpu /sys/fs/cgroup/cgroup.controllers
check "memory controller" grep -qw memory /sys/fs/cgroup/cgroup.controllers
check "pids controller" grep -qw pids /sys/fs/cgroup/cgroup.controllers
check "user namespace" unshare --user --map-root-user true
check "mount namespace" unshare --mount true
check "pid namespace" unshare --pid --fork true
check "network namespace" unshare --net true
check "no_new_privs support" sh -c 'command -v setpriv >/dev/null && setpriv --no-new-privs true'

if [ -w /sys/fs/cgroup/cgroup.subtree_control ]; then
  echo "PASS  cgroup subtree writable at current boundary"
else
  echo "FAIL  cgroup subtree not writable at current boundary"
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "Q12_HOST_READINESS=PASS_CANDIDATE"
  echo "NOTE=This is readiness only; authoritative Q12 execution evidence is still required."
else
  echo "Q12_HOST_READINESS=FAIL"
  exit 1
fi
