#!/usr/bin/env bash
echo "=== ก่อนเริ่ม ==="; df -h / | tail -1

echo; echo "=== 1) ลบแคชที่โหลดใหม่ได้ (~1.1GB+) ==="
uv cache clean 2>/dev/null; rm -rf /root/.cache/uv
pip cache purge 2>/dev/null
npm cache clean --force 2>/dev/null
apt-get clean
journalctl --vacuum-size=100M

echo; echo "=== 2) Docker image ที่ไม่มี container ใช้ ==="
docker rmi ghcr.io/astral-sh/uv:latest node:22-bookworm-slim 2>/dev/null
if systemctl cat ck-search-gateway 2>/dev/null | grep -q 'ck-search-gateway:local'; then
  echo "ข้าม ck-search-gateway:local (systemd ยังอ้างถึง)"
else
  read -rp "ลบ image ck-search-gateway:local (776MB)? [y/N] " a
  [ "$a" = y ] && docker rmi ck-search-gateway:local
fi

echo; echo "=== 3) sandboxes (2.4GB) ==="
du -xh --max-depth=1 /root/.local/state/sandboxes | sort -hr | head -15
echo "--- ที่ไม่ถูกแก้ไขเกิน 3 วัน ---"
find /root/.local/state/sandboxes -mindepth 1 -maxdepth 1 -mtime +3 -exec du -sh {} \;
pgrep -af sandbox | head -5
read -rp "ลบรายการเกิน 3 วันข้างบน? [y/N] " a
[ "$a" = y ] && find /root/.local/state/sandboxes -mindepth 1 -maxdepth 1 -mtime +3 -exec rm -rf {} +

echo; echo "=== 4) ตรวจต่อ (อ่านอย่างเดียว) ==="
echo "--- /usr ---";  du -xh --max-depth=2 /usr 2>/dev/null | sort -hr | head -12
echo "--- /opt ---";  du -xh --max-depth=2 /opt 2>/dev/null | sort -hr | head -8
echo "--- /home ---"; du -xh --max-depth=1 /home 2>/dev/null | sort -hr | head -5
echo "--- RAM ---";   free -h; ps aux --sort=-%mem | head -8 | cut -c1-150
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}'

echo; echo "=== หลังเสร็จ ==="; df -h / | tail -1
