#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

LOG="/root/cknexus-final-cleanup-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOG") 2>&1

echo "===== CK-NEXUS FINAL SAFE CLEANUP ====="
date -Is
df -hT /

echo
echo "===== 1. APT CACHE ====="
apt-get clean

echo
echo "===== 2. OLD TEMP FILES (>7 DAYS) ====="
find /tmp -xdev -type f -mtime +7 -print -delete 2>/dev/null || true
find /var/tmp -xdev -type f -mtime +7 -print -delete 2>/dev/null || true

echo
echo "===== 3. PYTHON BYTECODE IN CK-NEXUS ====="
if [ -d /root/ck-nexus ]; then
  find /root/ck-nexus -xdev -type d -name __pycache__ \
    -prune -print -exec rm -rf -- {} +
  find /root/ck-nexus -xdev -type f -name '*.pyc' -print -delete
fi

echo
echo "===== 4. ABANDONED CODEX TEMP CLONE ====="
TARGET=/root/.codex/.tmp/plugins-clone-qWLkeq
if [ -d "$TARGET" ] &&
   ! ps -eo args= | grep -F "$TARGET" | grep -v grep >/dev/null; then
  du -sh "$TARGET"
  rm -rf -- "$TARGET"
else
  echo "Skipped: absent or process reference detected"
fi

echo
echo "===== 5. SYSTEM JOURNAL RETENTION ====="
journalctl --rotate
journalctl --vacuum-time=14d

echo
echo "===== 6. DOCKER UNUSED RESOURCES (NO VOLUMES) ====="
docker system prune -f

echo
echo "===== 7. FINAL DISK STATUS ====="
sync
df -hT /
df -ih /

echo
echo "===== 8. RUNNING CONTAINERS ====="
docker ps --format 'table {{.Names}}\t{{.Status}}'

echo
echo "===== 9. CRITICAL SERVICES ====="
systemctl is-active \
  docker.service \
  cknexus-api-gateway.service \
  cknexus-mcp.service \
  cknexus-scanner.service \
  desktop-commander.service \
  n8n.service || true

echo
echo "===== 10. REMAINING LARGE DIRECTORIES ====="
du -xhd1 /var/lib /root/.local/state /opt 2>/dev/null | sort -h | tail -30

echo
echo "===== COMPLETE ====="
echo "Report: $LOG"
echo "Protected: Docker volumes, active container data, Sandbox state,"
echo "Containerd internals, credentials, recovery files and project source."
