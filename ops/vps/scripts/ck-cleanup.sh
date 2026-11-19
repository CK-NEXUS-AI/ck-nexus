#!/bin/bash
# CK-NEXUS VPS Cleanup
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

echo "============================================"
echo " CK-NEXUS VPS Cleanup"
echo "============================================"
echo ""

# ก่อน
BEFORE=$(df / | tail -1 | awk '{print $4}')
log "Disk free before: $((BEFORE/1024)) MB"

# 1. ไฟล์ชื่อแปลก (copy-paste ผิด)
echo ""
log "ลบไฟล์ชื่อแปลก..."
rm -f ~/'er --jq .login' 2>/dev/null && log "  ลบ: er --jq .login"
rm -f ~/'udo systemctl enable --now tailscaled' 2>/dev/null && log "  ลบ: udo systemctl..."
rm -f ~/o 2>/dev/null && log "  ลบ: o"
rm -f ~/nano.*.save 2>/dev/null && log "  ลบ: nano.*.save"

# 2. Script เก่า (ซ้ำ)
echo ""
log "ลบ script เก่า..."
for f in ck-nexus-q10-v3.sh.save ck-nexus-q10-v5.sh.save \
         ck-nexus-q10-v7.sh.save ck-nexus-q10-auto.sh.save \
         auto-setup.sh.save; do
  [ -f ~/"$f" ] && rm -f ~/"$f" && log "  ลบ: $f"
done

# 3. Empty dirs
echo ""
log "ลบ empty dirs..."
find ~ -maxdepth 1 -type d -empty -not -path ~ -not -name ".*" 2>/dev/null | while read d; do
  rmdir "$d" 2>/dev/null && log "  ลบ: $(basename $d)"
done

# 4. Temp files
echo ""
log "ลบ temp files..."
rm -rf /tmp/sbx-* /tmp/q10-* /tmp/codex-* /tmp/check-* 2>/dev/null
log "  ลบ temp แล้ว"

# หลัง
echo ""
AFTER=$(df / | tail -1 | awk '{print $4}')
DIFF=$((AFTER-BEFORE))
log "Disk free after: $((AFTER/1024)) MB"
log "Reclaimed: $((DIFF/1024)) MB"
echo ""
warn "Recovery captures + evidence ไม่ถูกลบ"
echo "============================================"
