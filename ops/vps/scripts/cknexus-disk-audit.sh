#!/usr/bin/env bash
set -u
LOG="/root/cknexus-disk-audit-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee "$LOG") 2>&1

echo "=== DISK ==="
df -hT /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS

echo
echo "=== TOP LEVEL ROOT USAGE ==="
du -xhd1 / 2>/dev/null | sort -h

echo
echo "=== SANDBOX DIRECTORY BREAKDOWN ==="
du -xhd2 /root/.local/state/sandboxes 2>/dev/null | sort -h | tail -50

echo
echo "=== CONTAINERD NAMESPACES ==="
if command -v ctr >/dev/null 2>&1; then
  ctr namespaces list
  for ns in $(ctr namespaces list -q 2>/dev/null); do
    echo "--- namespace: $ns ---"
    ctr -n "$ns" containers list 2>/dev/null || true
    ctr -n "$ns" images list 2>/dev/null || true
  done
fi

echo
echo "=== SNAP USAGE ==="
snap list --all 2>/dev/null || true
du -xhd2 /var/lib/snapd 2>/dev/null | sort -h | tail -30

echo
echo "=== DOCKER USAGE ==="
docker system df -v 2>/dev/null || true

echo
echo "=== ACTIVE SANDBOX / DESKTOP COMMANDER PROCESSES ==="
ps -eo pid,ppid,etime,args |
  grep -Ei 'sandbox|containerd|desktop-commander|openclaw' |
  grep -v grep || true

echo
echo "=== LARGE FILES (>200 MB), TOP 100 ==="
find /root /opt /var -xdev -type f -size +200M \
  -printf '%s %p\n' 2>/dev/null |
  sort -nr | head -100 |
  awk '{printf "%.2f GB  ", $1/1073741824; $1=""; sub(/^ /,""); print}'

echo
echo "=== SERVICES ==="
systemctl --no-pager --type=service --state=running

echo
echo "=== REPORT ==="
echo "$LOG"
