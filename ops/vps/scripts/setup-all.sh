#!/usr/bin/env bash
set +e

# --- [1] แก้ DNS ---
sudo mkdir -p /etc/systemd/resolved.conf.d
sudo tee /etc/systemd/resolved.conf.d/dns.conf > /dev/null << 'EOF'
[Resolve]
DNS=8.8.8.8 1.1.1.1
FallbackDNS=9.9.9.9
EOF
sudo systemctl restart systemd-resolved

# --- [2] ติดตั้ง sbx CLI ---
if ! command -v sbx &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  curl -fsSL https://sbx.docker.com/install.sh | sh || true
fi
command -v sbx >/dev/null && echo "sbx OK" || echo "sbx ยังไม่ติดตั้ง"

# --- [3] ตั้งค่า SSH sandbox ---
sbx setup ssh

# --- [4] SSH auto-accept + keepalive ---
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/config && chmod 600 ~/.ssh/config
grep -q "StrictHostKeyChecking accept-new" ~/.ssh/config || cat >> ~/.ssh/config << 'EOF'
Host *
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
    ServerAliveCountMax 3
EOF

# --- [5] alias vps ---
grep -q "vps()" ~/.bashrc || cat >> ~/.bashrc << 'EOF'
vps() {
  ssh -o StrictHostKeyChecking=accept-new root@162.35.28.151
}
EOF
source ~/.bashrc

# --- [6] ทดสอบ sandbox ---
ssh -o BatchMode=yes -o ConnectTimeout=10 c7d9vw.sbx "echo 'sandbox OK'; uname -a" \
  || echo "เชื่อม sandbox ไม่ได้ ลอง: ssh c7d9vw.sbx"

# --- [7] เปิดพอร์ต ---
sbx ports c7d9vw --publish 8080:8080 2>/dev/null \
  || echo "เปิดพอร์ตไม่สำเร็จ - ดูคำสั่งด้วย: sbx --help"

# --- [8] เคลียร์ดิสก์ ---
docker system prune -af --volumes 2>/dev/null
sudo apt-get autoremove -y
sudo apt-get clean

# --- [9] สรุป ---
echo ""
echo "========== เสร็จแล้ว =========="
echo "เข้า sandbox : ssh c7d9vw.sbx"
echo "เข้า VPS     : vps"
echo "================"
