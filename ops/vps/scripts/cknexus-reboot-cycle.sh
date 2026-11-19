#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=/root/cknexus-reboot-cycle-${TS}.log
exec > >(tee -a "$LOG") 2>&1

echo "=== [1/5] PRE-REBOOT CHECKS — $(date -u) ==="
uptime
uname -r
echo "--- reboot-required ---"; cat /var/run/reboot-required 2>/dev/null || true
cat /var/run/reboot-required.pkgs 2>/dev/null || true
echo "--- systemd enabled ---"
systemctl is-enabled n8n docker
echo "--- n8n ---"
systemctl is-active n8n
curl -sf -o /dev/null -w 'n8n healthz: %{http_code}\n' http://127.0.0.1:5678/healthz || echo "n8n healthz: FAIL"
echo "--- docker ---"
docker ps --format 'table {{.Names}}\t{{.Status}}'

echo
echo "=== [2/5] PRE-REBOOT CAPTURE — $(date -u) ==="
D=/root/cknexus-recovery-capture-${TS}-pre-reboot
mkdir -p "$D"
cp /root/.n8n/database.sqlite "$D/" 2>/dev/null || true
systemctl cat n8n > "$D/n8n.service"
uname -a            > "$D/uname.txt"
docker ps           > "$D/docker-ps.txt"
systemctl status n8n --no-pager > "$D/n8n-status.txt" || true
tar czf "${D}.tar.gz" -C /root "$(basename "$D")"
sha256sum "${D}.tar.gz" > "${D}.tar.gz.sha256"
echo "capture: ${D}.tar.gz"

echo
echo "=== [3/5] INSTALL POST-BOOT VERIFY UNIT — $(date -u) ==="
cat > /etc/systemd/system/cknexus-postboot-verify.service <<UNIT
[Unit]
Description=CK-Nexus post-boot verification
After=n8n.service docker.service network-online.target
Wants=network-online.target
ConditionPathExists=!/root/.cknexus-postboot-done

[Service]
Type=oneshot
ExecStart=/root/cknexus-postboot-verify.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

cat > /root/cknexus-postboot-verify.sh <<'PBS'
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
PBS
chmod +x /root/cknexus-postboot-verify.sh
systemctl daemon-reload
systemctl enable cknexus-postboot-verify.service
echo "post-boot unit armed"

echo
echo "=== [4/5] SYNC — $(date -u) ==="
sync
echo "sync done"

echo
echo "=== [5/5] SCHEDULING REBOOT in 60s — $(date -u) ==="
echo "reconnect in ~2 min and run:"
echo "  uptime && uname -r"
echo "  cat /root/cknexus-postboot-verify-*.txt | tail -50"
shutdown -r +1 "CK-Nexus: reboot for kernel 6.8.0-146 + libc6 + apparmor"
