#!/usr/bin/env bash
set -euo pipefail

# Development/closure-preparation helper only.
# This script qualifies a host. It never creates Q10 PASS evidence and never
# changes the frozen Q10 subject or governance state.

SUBJECT="39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
TREE="0525195934f703a8becf8a39f6397b2411e0bb2e"
OUT="${Q10_HOST_EVIDENCE_DIR:-$PWD/q10-host-evidence}"
RESULTS="$OUT/checks.tsv"
SETUP="$OUT/host-setup.md"
CONFIG_SUMS="$OUT/SHA256SUMS.config"
MIN_CPU=4
MIN_RAM_BYTES=$((16 * 1024 * 1024 * 1024))
MIN_DISK_BYTES=$((100 * 1024 * 1024 * 1024))

umask 077
mkdir -p "$OUT"
: > "$RESULTS"
: > "$CONFIG_SUMS"

failures=0
now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

record() {
  local status="$1" name="$2" detail="$3"
  printf '%s\t%s\t%s\n' "$status" "$name" "$detail" >> "$RESULTS"
  printf '%-5s %-32s %s\n' "$status" "$name" "$detail"
  if [ "$status" = "FAIL" ]; then
    failures=$((failures + 1))
  fi
}

require_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    record PASS "command:$cmd" "present"
  else
    record FAIL "command:$cmd" "missing"
  fi
}

bytes_ge() {
  [ "${1:-0}" -ge "$2" ] 2>/dev/null
}

version_ge_310() {
  python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

os_allowed() {
  # WP1 Final Integrated Order: Ubuntu 22.04 LTS or RHEL 9.
  # Do not silently broaden this allowlist.
  . /etc/os-release
  case "${ID:-}:${VERSION_ID:-}" in
    ubuntu:22.04|rhel:9|rhel:9.*) return 0 ;;
    *) return 1 ;;
  esac
}

cgroup_v2_ok() {
  [ "$(stat -fc %T /sys/fs/cgroup 2>/dev/null || true)" = "cgroup2fs" ] || return 1
  [ -r /sys/fs/cgroup/cgroup.controllers ] || return 1
  grep -qw cpu /sys/fs/cgroup/cgroup.controllers || return 1
  grep -qw memory /sys/fs/cgroup/cgroup.controllers || return 1
  grep -qw pids /sys/fs/cgroup/cgroup.controllers || return 1
}

userns_ok() {
  unshare --user --map-root-user true
}

namespace_stack_ok() {
  unshare --user --map-root-user --mount --pid --fork --net true
}

bwrap_ok() {
  bwrap --ro-bind / / --proc /proc --dev /dev true
}

sshd_ok() {
  systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd 2>/dev/null
}

audit_ok() {
  systemctl is-active --quiet auditd 2>/dev/null
}

time_sync_ok() {
  [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null || true)" = "yes" ]
}

docker_ok() {
  docker info >/dev/null 2>&1
}

internet_ok() {
  curl -fsSIL --max-time 10 https://github.com/ >/dev/null
}

ssd_ok() {
  local root_source parent rota
  root_source="$(findmnt -n -o SOURCE / 2>/dev/null || true)"
  [ -n "$root_source" ] || return 1
  parent="$(lsblk -ndo PKNAME "$root_source" 2>/dev/null | head -n1 || true)"
  if [ -n "$parent" ]; then
    rota="$(lsblk -ndo ROTA "/dev/$parent" 2>/dev/null | head -n1 | tr -d ' ' || true)"
  else
    rota="$(lsblk -ndo ROTA "$root_source" 2>/dev/null | head -n1 | tr -d ' ' || true)"
  fi
  [ "$rota" = "0" ]
}

printf 'CK-NEXUS Q10 execution-host qualification\n'
printf 'frozen_subject=%s\n' "$SUBJECT"
printf 'frozen_tree=%s\n' "$TREE"
printf 'generated_at=%s\n' "$(now_utc)"

for cmd in git python3 docker unshare setpriv bwrap curl findmnt lsblk sha256sum systemctl timedatectl; do
  require_cmd "$cmd"
done

if [ -r /etc/os-release ] && os_allowed; then
  . /etc/os-release
  record PASS os_allowlist "${PRETTY_NAME:-unknown}"
else
  pretty="$(. /etc/os-release 2>/dev/null; printf '%s' "${PRETTY_NAME:-unknown}")"
  record FAIL os_allowlist "$pretty"
fi

cpu_count="$(nproc 2>/dev/null || echo 0)"
if bytes_ge "$cpu_count" "$MIN_CPU"; then
  record PASS cpu_cores "$cpu_count >= $MIN_CPU"
else
  record FAIL cpu_cores "$cpu_count < $MIN_CPU"
fi

ram_bytes="$(awk '/^MemTotal:/ {print $2 * 1024; exit}' /proc/meminfo 2>/dev/null | cut -d. -f1)"
ram_bytes="${ram_bytes:-0}"
if bytes_ge "$ram_bytes" "$MIN_RAM_BYTES"; then
  record PASS ram_bytes "$ram_bytes >= $MIN_RAM_BYTES"
else
  record FAIL ram_bytes "$ram_bytes < $MIN_RAM_BYTES"
fi

disk_bytes="$(df -B1 --output=size / 2>/dev/null | tail -n1 | tr -d ' ')"
disk_bytes="${disk_bytes:-0}"
if bytes_ge "$disk_bytes" "$MIN_DISK_BYTES"; then
  record PASS root_storage_bytes "$disk_bytes >= $MIN_DISK_BYTES"
else
  record FAIL root_storage_bytes "$disk_bytes < $MIN_DISK_BYTES"
fi

if ssd_ok; then record PASS root_storage_ssd "non-rotational"; else record FAIL root_storage_ssd "not proven non-rotational"; fi
if version_ge_310; then record PASS python_version "$(python3 --version 2>&1)"; else record FAIL python_version "$(python3 --version 2>&1 || true)"; fi
if [ -d /run/systemd/system ]; then record PASS systemd "available"; else record FAIL systemd "not available"; fi
if cgroup_v2_ok; then record PASS cgroup_v2 "cpu,memory,pids available"; else record FAIL cgroup_v2 "required controllers not proven"; fi
if userns_ok >/dev/null 2>&1; then record PASS user_namespace "unprivileged mapping works"; else record FAIL user_namespace "unshare failed"; fi
if namespace_stack_ok >/dev/null 2>&1; then record PASS namespace_stack "user+mount+pid+net works"; else record FAIL namespace_stack "combined namespace test failed"; fi
if setpriv --no-new-privs true >/dev/null 2>&1; then record PASS no_new_privs "supported"; else record FAIL no_new_privs "setpriv test failed"; fi
if bwrap_ok >/dev/null 2>&1; then record PASS bubblewrap "sandbox smoke test passed"; else record FAIL bubblewrap "sandbox smoke test failed"; fi
if docker_ok; then record PASS docker_daemon "docker info passed"; else record FAIL docker_daemon "docker info failed"; fi
if sshd_ok; then record PASS ssh_service "active"; else record FAIL ssh_service "not active"; fi
if audit_ok; then record PASS auditd "active"; else record FAIL auditd "not active"; fi
if time_sync_ok; then record PASS time_sync "NTP synchronized"; else record FAIL time_sync "NTP synchronization not proven"; fi
if internet_ok; then record PASS internet_egress "HTTPS to github.com passed"; else record FAIL internet_egress "HTTPS egress failed"; fi

for cfg in \
  /etc/os-release \
  /etc/ssh/sshd_config \
  /etc/docker/daemon.json \
  /etc/audit/auditd.conf \
  /etc/systemd/journald.conf \
  /etc/systemd/timesyncd.conf; do
  if [ -f "$cfg" ] && [ -r "$cfg" ]; then
    sha256sum "$cfg" >> "$CONFIG_SUMS"
  fi
done

kernel="$(uname -srmo 2>/dev/null || echo unknown)"
hostname_value="$(hostname 2>/dev/null || echo unknown)"
uid_value="$(id -u)"
user_value="$(id -un)"

{
  printf '# CK-NEXUS Q10 Execution Host Setup Record\n\n'
  printf 'Status: HOST_QUALIFICATION_CANDIDATE\n\n'
  printf 'This document is generated on the execution host. It does not certify Q10 and does not replace independent human review or owner sign-off.\n\n'
  printf '## Frozen subject boundary\n\n'
  printf -- '- Commit: `%s`\n' "$SUBJECT"
  printf -- '- Tree: `%s`\n' "$TREE"
  printf -- '- Generated UTC: `%s`\n\n' "$(now_utc)"
  printf '## Host facts\n\n'
  printf -- '- Hostname: `%s`\n' "$hostname_value"
  printf -- '- Kernel: `%s`\n' "$kernel"
  printf -- '- Operator UID/User: `%s/%s`\n' "$uid_value" "$user_value"
  printf -- '- CPU cores: `%s`\n' "$cpu_count"
  printf -- '- RAM bytes: `%s`\n' "$ram_bytes"
  printf -- '- Root filesystem bytes: `%s`\n\n' "$disk_bytes"
  printf '## Qualification results\n\n'
  printf '| Result | Check | Detail |\n|---|---|---|\n'
  while IFS=$'\t' read -r status name detail; do
    detail="${detail//|/\\|}"
    printf '| %s | `%s` | %s |\n' "$status" "$name" "$detail"
  done < "$RESULTS"
  printf '\n## Configuration checksums\n\n'
  if [ -s "$CONFIG_SUMS" ]; then
    printf 'Checksums are stored separately in `SHA256SUMS.config`. File contents are not copied into this evidence record.\n'
  else
    printf 'No readable configuration files were available for checksum capture.\n'
  fi
  printf '\n## Authority note\n\n'
  printf 'A PASS here means only that this host satisfies the automated WP1 qualification checks. Canonical scans must still bind to the exact frozen subject, and Q10 remains NOT_VERIFIED until canonical evidence, Darker verification, independent HUMAN review, and owner HUMAN sign-off are complete.\n'
} > "$SETUP"

sha256sum "$RESULTS" "$SETUP" "$CONFIG_SUMS" > "$OUT/SHA256SUMS"

if [ "$failures" -eq 0 ]; then
  printf 'Q10_HOST_QUALIFICATION=PASS_CANDIDATE\n'
  exit 0
fi

printf 'Q10_HOST_QUALIFICATION=FAIL failures=%s\n' "$failures" >&2
exit 1
