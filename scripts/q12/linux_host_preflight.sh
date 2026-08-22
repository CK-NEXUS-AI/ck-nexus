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

current_cgroup_path() {
  awk -F: '$1=="0" && $2=="" {print $3; exit}' /proc/self/cgroup
}

enabled_controller() {
  local file="$1" controller="$2"
  tr ' ' '\n' < "$file" | sed 's/^[+-]//' | grep -qx "$controller"
}

echo "CK-NEXUS Q12 Linux Host Preflight"
echo "kernel=$(uname -srmo)"
echo "uid=$(id -u) user=$(id -un)"
echo "cgroup_fs=$(stat -fc %T /sys/fs/cgroup 2>/dev/null || echo unavailable)"

check "non-root operator" test "$(id -u)" -ne 0
check "systemd available" test -d /run/systemd/system
check "unshare available" command -v unshare
check "setpriv available" command -v setpriv
check "cgroup v2 mounted" test "$(stat -fc %T /sys/fs/cgroup 2>/dev/null || true)" = "cgroup2fs"
check "root controllers file" test -r /sys/fs/cgroup/cgroup.controllers
check "cpu controller available" grep -qw cpu /sys/fs/cgroup/cgroup.controllers
check "memory controller available" grep -qw memory /sys/fs/cgroup/cgroup.controllers
check "pids controller available" grep -qw pids /sys/fs/cgroup/cgroup.controllers

cg_rel="$(current_cgroup_path || true)"
if [ -n "$cg_rel" ]; then
  cg_abs="/sys/fs/cgroup${cg_rel}"
  echo "cgroup_path=$cg_rel"
  check "current cgroup exists" test -d "$cg_abs"
  check "delegated controllers readable" test -r "$cg_abs/cgroup.controllers"
  check "delegated subtree control exists" test -e "$cg_abs/cgroup.subtree_control"
  check "delegated subtree writable" test -w "$cg_abs/cgroup.subtree_control"
  check "delegated cpu controller" enabled_controller "$cg_abs/cgroup.controllers" cpu
  check "delegated memory controller" enabled_controller "$cg_abs/cgroup.controllers" memory
  check "delegated pids controller" enabled_controller "$cg_abs/cgroup.controllers" pids
  check "cpu enabled for child cgroups" enabled_controller "$cg_abs/cgroup.subtree_control" cpu
  check "memory enabled for child cgroups" enabled_controller "$cg_abs/cgroup.subtree_control" memory
  check "pids enabled for child cgroups" enabled_controller "$cg_abs/cgroup.subtree_control" pids
else
  echo "FAIL  current unified cgroup path unavailable"
  fail=1
fi

check "unprivileged user namespace" unshare --user --map-root-user true
check "combined user+mount namespace" unshare --user --map-root-user --mount true
check "combined user+pid namespace" unshare --user --map-root-user --pid --fork true
check "combined user+network namespace" unshare --user --map-root-user --net true
check "authoritative namespace stack" unshare --user --map-root-user --mount --pid --fork --net true
check "no_new_privs support" setpriv --no-new-privs true

if [ "$fail" -eq 0 ]; then
  echo "Q12_HOST_READINESS=PASS_CANDIDATE"
  echo "NOTE=Readiness only. It does not create Q12 PASS evidence or prove cgroup limits/escape resistance."
else
  echo "Q12_HOST_READINESS=FAIL"
  exit 1
fi
