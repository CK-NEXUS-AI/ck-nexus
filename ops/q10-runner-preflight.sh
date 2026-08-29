#!/usr/bin/env bash
set -euo pipefail

fail(){ echo "Q10_RUNNER_PREFLIGHT=BLOCKED:$1" >&2; exit 30; }

[ "$(uname -s)" = "Linux" ] || fail non_linux
[ -r /etc/os-release ] || fail os_release_missing
. /etc/os-release
printf 'OS=%s %s\n' "${ID:-unknown}" "${VERSION_ID:-unknown}"

command -v git >/dev/null || fail git_missing
command -v python3 >/dev/null || fail python3_missing
command -v sha256sum >/dev/null || fail sha256sum_missing
command -v curl >/dev/null || fail curl_missing

mem_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)
[ "${mem_kb:-0}" -ge 1048576 ] || fail memory_lt_1g
free_kb=$(df -Pk . | awk 'NR==2{print $4}')
[ "${free_kb:-0}" -ge 5242880 ] || fail disk_lt_5g

[ -r /sys/fs/cgroup/cgroup.controllers ] || fail cgroup_v2_missing
controllers=$(cat /sys/fs/cgroup/cgroup.controllers)
for c in cpu memory pids; do
  printf '%s\n' "$controllers" | grep -qw "$c" || fail "cgroup_${c}_missing"
done

printf 'ARCH=%s\n' "$(uname -m)"
printf 'PYTHON=%s\n' "$(python3 --version 2>&1)"
printf 'GIT=%s\n' "$(git --version)"
printf 'CGROUP_CONTROLLERS=%s\n' "$controllers"
printf 'Q10_RUNNER_PREFLIGHT=VERIFIED\n'
