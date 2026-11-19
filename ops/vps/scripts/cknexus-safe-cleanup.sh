#!/usr/bin/env bash
set -Eeuo pipefail

echo "===== CK-NEXUS SAFE CLEANUP ====="
date -Is
df -hT /

echo
echo "===== 1. CLEAN APT CACHE ====="
apt-get clean

echo
echo "===== 2. CLEAN OLD TEMP FILES ====="
# ลบเฉพาะไฟล์ปกติใน /tmp และ /var/tmp
# ที่ไม่มีการแก้ไขเกิน 7 วัน
find /tmp -xdev -type f -mtime +7 \
  -print -delete 2>/dev/null || true

find /var/tmp -xdev -type f -mtime +7 \
  -print -delete 2>/dev/null || true

echo
echo "===== 3. CLEAN USER CACHE FILES ====="
# ลบเฉพาะ cache ของ Mesa ที่สร้างใหม่ได้
if [ -d /root/.cache/mesa_shader_cache ]; then
  du -sh /root/.cache/mesa_shader_cache
  rm -rf -- /root/.cache/mesa_shader_cache
fi

echo
echo "===== 4. CLEAN NPM CACHE ====="
# npm cache เป็นข้อมูลดาวน์โหลดที่สร้างใหม่ได้
if command -v npm >/dev/null 2>&1; then
  npm cache clean --force
else
  echo "npm command unavailable; skipped"
fi

echo
echo "===== 5. VACUUM OLD SYSTEM JOURNAL ====="
# เก็บ system journal ล่าสุดไว้ ไม่หยุดบริการ
journalctl --rotate
journalctl --vacuum-time=14d

echo
echo "===== 6. FINAL DISK STATUS ====="
sync
df -hT /
df -ih /

echo
echo "===== CLEANUP FINISHED ====="
echo "No Docker images, containers, volumes, project files,"
echo "credentials, backups, or sandbox state were deleted."
