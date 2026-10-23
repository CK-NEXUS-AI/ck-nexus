#!/usr/bin/env bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT=/root/cknexus-postboot-verify-${TS}.txt
{
  echo "=== POST-BOOT VERIFY — $(date -u) ==="
  uptime
  echo "kernel: $(uname -r)"
  echo "--- reboot-required ---"
  cat /var/run/reboot-required 2>/dev/null || echo "clear"
  echo "--- n8n ---"
  systemctl is-active n8n
  systemctl status n8n --no-pager | head -15
  curl -sf -o /dev/null -w 'n8n healthz: %{http_code}\n' http://127.0.0.1:5678/healthz || echo "n8n healthz: FAIL"
  echo "--- docker ---"
  docker ps --format 'table {{.Names}}\t{{.Status}}'
} > "$OUT" 2>&1

D=/root/cknexus-recovery-capture-${TS}-post-reboot
mkdir -p "$D"
cp /root/.n8n/database.sqlite "$D/" 2>/dev/null || true
systemctl cat n8n > "$D/n8n.service"
uname -a          > "$D/uname.txt"
docker ps         > "$D/docker-ps.txt"
cp "$OUT" "$D/"
tar czf "${D}.tar.gz" -C /root "$(basename "$D")"
sha256sum "${D}.tar.gz" > "${D}.tar.gz.sha256"
touch /root/.cknexus-postboot-done
echo "post-boot capture: ${D}.tar.gz" >> "$OUT"
