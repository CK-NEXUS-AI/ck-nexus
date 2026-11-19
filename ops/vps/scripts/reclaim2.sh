#!/usr/bin/env bash
echo "=== ก่อนเริ่ม ==="; df -h / | tail -1

echo; echo "=== A) เช็ก service ที่อาจพังจากการลบ image ==="
systemctl is-active ck-search-gateway ck-search-gateway-tunnel
journalctl -u ck-search-gateway -n 8 --no-pager | cut -c1-160
docker ps --format '{{.Names}}' | grep -i search

echo; echo "=== B) ตัวกินพื้นที่ (อ่านอย่างเดียว) ==="
echo "--- node_modules global ---"
du -xsh /usr/lib/node_modules/* 2>/dev/null | sort -hr | head -12
npm ls -g --depth=0 2>/dev/null
echo "--- google cloud ---"
dpkg -l | awk '/google-cloud/{print $2, $3}'
echo "--- swap ---"
ls -lh /swapfile2 /home/swapfile 2>/dev/null
echo "--- sandboxes ---"
du -xh --max-depth=2 /root/.local/state/sandboxes 2>/dev/null | sort -hr | head -8
sbx --help 2>&1 | head -15
echo "--- uv cache ---"
du -sh /root/.cache/uv 2>/dev/null || echo "uv cache หายแล้ว"

echo; echo "=== C) ลบ (ถามก่อนทุกขั้น) ==="
read -rp "ลบ google-cloud-sdk (~810MB)? [y/N] " a
if [ "$a" = y ]; then
  apt-get remove --purge -y google-cloud-cli google-cloud-sdk 2>/dev/null
  apt-get autoremove -y
fi

echo "ใส่ชื่อ npm global ที่จะลบ (คั่นด้วยช่องว่าง, ว่าง = ข้าม):"
read -r pk
[ -n "$pk" ] && npm uninstall -g $pk

apt-get clean
echo; echo "=== หลังเสร็จ ==="; df -h / | tail -1
free -h | head -2
