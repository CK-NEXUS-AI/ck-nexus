#!/usr/bin/env bash
set -u

REPORT="/root/cknexus-rm-audit-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee "$REPORT") 2>&1

echo "===== CK-NEXUS SAFE REMOVAL AUDIT ====="
date -Is
echo "MODE: READ-ONLY — NO FILES WILL BE DELETED"

echo
echo "===== 1. DISK SPACE ====="
df -hT /
du -xhd1 / 2>/dev/null | sort -h

echo
echo "===== 2. LARGE DIRECTORIES IN ROOT HOME ====="
du -xhd1 /root 2>/dev/null | sort -h

echo
echo "===== 3. OLD BACKUPS AND ARCHIVES — REVIEW ONLY ====="
find /root -xdev -type f \
  \( -iname '*.bak' -o -iname '*.old' -o -iname '*.orig' \
     -o -iname '*.tar' -o -iname '*.tar.gz' -o -iname '*.tgz' \
     -o -iname '*.zip' -o -iname '*.log.*' \) \
  -printf '%TY-%Tm-%Td %10s bytes %p\n' 2>/dev/null |
  sort

echo
echo "===== 4. TEMPORARY FILES — REVIEW ONLY ====="
find /tmp /var/tmp -xdev -type f \
  -printf '%TY-%Tm-%Td %10s bytes %p\n' 2>/dev/null |
  sort

echo
echo "===== 5. EMPTY FILES — REVIEW ONLY ====="
find /root -xdev -type f -empty \
  -printf '%TY-%Tm-%Td %p\n' 2>/dev/null |
  head -200

echo
echo "===== 6. LARGE FILES OVER 100 MB ====="
find /root /var/tmp /tmp -xdev -type f -size +100M \
  -printf '%s bytes %p\n' 2>/dev/null |
  sort -nr | head -100

echo
echo "===== 7. GIT REPOSITORIES AND WORKING TREE ====="
for repo in /root/ck-nexus /root/ck-nexus-agents /opt/cknexus; do
  if [ -d "$repo/.git" ]; then
    echo "--- $repo ---"
    git -C "$repo" status --short --branch 2>/dev/null || true
    git -C "$repo" count-objects -v 2>/dev/null || true
  fi
done

echo
echo "===== 8. RUNNING DOCKER CONTAINERS ====="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null || true

echo
echo "===== 9. DOCKER DISK USAGE ====="
docker system df -v 2>/dev/null || true

echo
echo "===== 10. SYSTEM SERVICES ====="
systemctl --no-pager --type=service --state=running 2>/dev/null || true

echo
echo "===== 11. SYSTEM LOG SIZE ====="
journalctl --disk-usage 2>/dev/null || true
du -sh /var/log /var/lib/containerd \
  /var/lib/docker /root/.local/state/sandboxes 2>/dev/null || true

echo
echo "===== 12. CREDENTIAL / RECOVERY FILE NAMES — PATHS ONLY ====="
find /root -xdev -type f \
  \( -iname '*.env' -o -iname '*credential*' -o -iname '*secret*' \
     -o -iname '*recovery*' -o -iname '*key*.json' \
     -o -iname '*evidence*' \) \
  -printf '%p\n' 2>/dev/null |
  head -200

echo
echo "===== AUDIT COMPLETE ====="
echo "Report: $REPORT"
echo "No files, containers, volumes, or services were removed."
