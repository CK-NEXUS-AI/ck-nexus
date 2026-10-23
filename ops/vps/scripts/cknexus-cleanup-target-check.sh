#!/usr/bin/env bash
set -u
LOG="/root/cknexus-cleanup-target-check-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee "$LOG") 2>&1

echo "=== 1. DISK STATUS ==="
df -hT /

echo
echo "=== 2. SNAP PACKAGES AND DEPENDENCIES ==="
snap list --all
for p in gnome-42-2204 gnome-46-2404 mesa-2404 firefox; do
  echo "--- snap: $p ---"
  snap info "$p" 2>/dev/null | grep -E '^(name|summary|installed|tracking|confinement):' || true
done

echo
echo "=== 3. CODEX EXECUTABLES ==="
find /root/.openclaw -xdev -type f -path '*/codex' \
  -printf '%s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null |
  sort -nr

echo
echo "=== 4. REFERENCES TO CODEX CAPTURE ==="
ps -eo pid,ppid,etime,args |
  grep -E 'openclaw|codex|plugin-captures' |
  grep -v grep || true

echo
echo "=== 5. OPENCLAW CAPTURE DIRECTORY ==="
find /root/.openclaw/tmp/plugin-captures -maxdepth 4 \
  -type f -printf '%s %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null |
  sort -nr | head -60

echo
echo "=== 6. SANDBOX MANAGEMENT COMMANDS ==="
for c in sbx sandboxctl sandboxd; do
  command -v "$c" 2>/dev/null || true
done
systemctl status desktop-commander.service --no-pager 2>/dev/null || true

echo
echo "=== 7. FINAL DISK STATUS ==="
df -hT /
echo "Report: $LOG"
