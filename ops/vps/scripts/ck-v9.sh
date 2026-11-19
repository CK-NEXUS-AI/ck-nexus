#!/bin/bash
# CK-NEXUS Q10 V9 — Auto-write + Run
set -o pipefail

TARGET_SHA="39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
TARGET_TREE="0525195934f703a8becf8a39f6397b2411e0bb2e"
TS=$(date +%s)
SANDBOX_NAME="ck-q10-$TS"
OUTPUT_DIR="$HOME/ck-q10-evidence-$TS"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
err()  { echo -e "${R}[✗]${N} $1"; }

echo "============================================================"
echo " CK-NEXUS Q10 V9"
echo "============================================================"

# ---------- STEP 1: Cleanup ----------
echo ""
log "STEP 1: Cleanup"
rm -rf /tmp/sbx-* /tmp/q10-* /tmp/codex-* 2>/dev/null
echo "y" | sbx --cloud rm sbx_001m4vjfrk7z6wxagqxr6gz2gtz 2>/dev/null || true
log "Cleanup เสร็จ"

# ---------- STEP 2: Choose Auth ----------
echo ""
echo "============================================================"
echo " เลือก Authentication Mode"
echo "============================================================"
echo "  [1] OAuth (ChatGPT Plus/Pro) — ฟรี"
echo "  [2] API Key (ต้องมีเครดิต)"
echo ""
read -rp "เลือก (1/2) [default: 1]: " AUTH_MODE
AUTH_MODE=${AUTH_MODE:-1}

if [ "$AUTH_MODE" = "1" ]; then
    warn "OAuth: ต้อง sign-in ผ่าน sandbox เอง"
    log "จะใช้ Codex OAuth (device auth) ภายใน sandbox"
else
    echo ""
    read -rsp "🔑 OpenAI API Key: " OK
    echo ""
    if [ -z "$OK" ]; then err "ไม่ได้ใส่ key"; exit 1; fi
    echo "$OK" | sbx secret set openai 2>&1 | tail -1
    unset OK
    log "บันทึก API Key แล้ว"
fi

# ---------- STEP 3: GitHub PAT ----------
echo ""
echo "============================================================"
echo " GitHub PAT (สำหรับ private repo)"
echo "============================================================"
read -rsp "🔑 GitHub PAT: " GH
echo ""
if [ -z "$GH" ]; then err "ไม่ได้ใส่ GH token"; exit 1; fi
echo "$GH" | sbx secret set github 2>&1 | tail -1
unset GH
log "บันทึก GitHub PAT แล้ว"

# ---------- STEP 4: Create Sandbox ----------
echo ""
log "STEP 4: สร้าง sandbox"
SANDBOX_ID=$(sbx --cloud run --detach \
    --name "$SANDBOX_NAME" \
    --ttl 4h \
    --on-timeout stop \
    --cpus 2 --memory 4g \
    --allow-network api.openai.com \
    --allow-network chatgpt.com \
    --allow-network auth.openai.com \
    --allow-network github.com \
    --allow-network raw.githubusercontent.com \
    --allow-network objects.githubusercontent.com \
    codex 2>&1 | grep -oE 'sbx_[a-z0-9]+' | head -1)

if [ -z "$SANDBOX_ID" ]; then
    err "สร้าง sandbox ล้มเหลว"
    exit 1
fi
log "Sandbox: $SANDBOX_ID"
sleep 10

# ---------- STEP 5: Test Codex ----------
echo ""
log "STEP 5: ทดสอบ Codex"
TEST_OUT=$(sbx --cloud exec "$SANDBOX_ID" \
    bash -c "cd /tmp && codex exec --skip-git-repo-check 'respond OK'" 2>&1)
echo "$TEST_OUT" | tail -5

if echo "$TEST_OUT" | grep -qi "no credits"; then
    echo ""
    err "Codex ไม่มีเครดิต — ต้องเติมที่ platform.openai.com"
    echo "   Sandbox: $SANDBOX_ID (เก็บไว้)"
    echo "   แก้ไขแล้วรันต่อ: sbx --cloud exec $SANDBOX_ID bash /tmp/q10-scan.sh"
    exit 1
fi

if echo "$TEST_OUT" | grep -qiE "^OK|respond.*OK"; then
    log "Codex พร้อมใช้งาน"
else
    warn "Codex response ไม่ชัดเจน — ตรวจสอบต่อ"
fi

# ---------- STEP 6: Create Scan Script ----------
echo ""
log "STEP 6: เตรียมสคริปต์สแกน"
cat > /tmp/q10-scan.sh << 'SCAN_EOF'
#!/bin/bash
mkdir -p ~/work ~/evidence && cd ~/work
echo "[1/5] Clone..."
git clone --depth 50 https://github.com/CK-NEXUS-AI/ck-nexus.git 2>&1 | tail -2
cd ck-nexus || exit 1
echo "[2/5] Checkout..."
git fetch --depth 50 origin 39f5c1adb9d761ab418cf088ff1f051b1ca731d1 2>&1 | tail -1
git checkout 39f5c1adb9d761ab418cf088ff1f051b1ca731d1 2>&1 | tail -1
H=$(git rev-parse HEAD)
T=$(git rev-parse HEAD^{tree})
[ "$H" != "39f5c1adb9d761ab418cf088ff1f051b1ca731d1" ] && exit 1
[ "$T" != "0525195934f703a8becf8a39f6397b2411e0bb2e" ] && exit 1
echo "[3/5] SHA/Tree OK"
echo "[4/5] Codex scan..."
codex exec --skip-git-repo-check "Deep security analysis. Focus: secrets, deps, auth, command injection, path traversal, prompt injection, privilege escalation, fail-open. For each: Severity, File:Line, Description, Fix." 2>&1 | tee ~/evidence/Q10_SCAN_REPORT.txt
echo "[5/5] Manifest..."
cd ~/evidence
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > MANIFEST.json << M
{"gate":"Q10","sha":"$H","tree":"$T","at":"$NOW","status":"NO-GO"}
M
sha256sum Q10_SCAN_REPORT.txt MANIFEST.json > SHA256SUMS
echo "DONE"
SCAN_EOF

sbx --cloud cp /tmp/q10-scan.sh "$SANDBOX_ID:/tmp/q10-scan.sh" || {
    err "คัดลอกสคริปต์ล้มเหลว"; exit 1
}
log "คัดลอกสคริปต์แล้ว"

# ---------- STEP 7: Run Scan ----------
echo ""
warn "STEP 7: รัน Q10 Scan (5-15 นาที)"
sbx --cloud exec "$SANDBOX_ID" bash /tmp/q10-scan.sh 2>&1 | tee /tmp/q10-scan.log

# ---------- STEP 8: Export ----------
echo ""
log "STEP 8: ดึงหลักฐาน"
mkdir -p "$OUTPUT_DIR"
sbx --cloud cp "$SANDBOX_ID:/root/evidence/." "$OUTPUT_DIR/" 2>/dev/null || \
sbx --cloud cp "$SANDBOX_ID:/home/codex/evidence/." "$OUTPUT_DIR/" 2>/dev/null || \
warn "ดึงอัตโนมัติล้มเหลว"
[ -d "$OUTPUT_DIR" ] && ls -la "$OUTPUT_DIR"

# ---------- Summary ----------
echo ""
echo "============================================================"
log "Sandbox: $SANDBOX_ID"
log "Evidence: $OUTPUT_DIR"
log "Log: /tmp/q10-scan.log"
echo "============================================================"
warn "Production: NO-GO"
echo "============================================================"
