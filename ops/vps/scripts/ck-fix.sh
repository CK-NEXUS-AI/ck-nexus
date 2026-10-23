#!/bin/bash
# CK-NEXUS Q10 — Fix + Run (ชุดเดียวจบ)
set -o pipefail

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

SANDBOX="sbx_001m4w3j1z26691b5t5xxpxmbh1"
TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q10-fix-$TS"
mkdir -p "$EVID"

echo ""
echo "============================================"
echo " CK-NEXUS Q10 Fix"
echo "============================================"
log "Sandbox: $SANDBOX"
log "Evidence: $EVID"
echo ""

# ============================================
# 1. TTL — ดู help ก่อน
# ============================================
echo "### 1. TTL Help ###"
sbx --cloud ttl --help 2>&1 | head -10 | tee "$EVID/ttl-help.txt"
echo ""

# ลอง syntax ที่ถูกต้อง
sbx --cloud ttl "$SANDBOX" 12h 2>&1 | tail -2 || \
sbx --cloud ttl "$SANDBOX" --ttl 12h 2>&1 | tail -2 || \
warn "TTL set failed — ตรวจ help ข้างบน"
echo ""

# ============================================
# 2. ติดตั้ง pytest + semgrep ใน sandbox
# ============================================
echo "### 2. Install Python Tools ###"
warn "ใช้เวลา 2-3 นาที"
echo ""

sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"

# ลองใช้ --break-system-packages
echo "=== Try pip install with --break-system-packages ==="
python3 -m pip install --break-system-packages --quiet pytest semgrep 2>&1 | tail -3
echo "exit: $?"

# ตรวจ
echo ""
echo "=== Verify ==="
python3 -m pytest --version 2>&1 | head -1
python3 -m semgrep --version 2>&1 | head -1
' 2>&1 | tee "$EVID/install-tools.log"
echo ""

# ============================================
# 3. รัน Pytest
# ============================================
echo "### 3. Run Pytest ###"
warn "ใช้เวลา 30-60 วินาที"
echo ""

sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/ck-nexus 2>/dev/null || cd ~/work/ck-nexus 2>/dev/null || exit 1
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -50
' 2>&1 | tee "$EVID/pytest.log"
echo ""

# ============================================
# 4. รัน Semgrep
# ============================================
echo "### 4. Run Semgrep ###"
warn "ใช้เวลา 60-120 วินาที"
echo ""

sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/ck-nexus 2>/dev/null || cd ~/work/ck-nexus 2>/dev/null || exit 1
python3 -m semgrep scan --config=auto --json . > /tmp/sg.json 2>/tmp/sg.err
echo "exit: $?"
echo "size: $(wc -c < /tmp/sg.json) bytes"
echo ""
echo "=== stderr (last 5) ==="
tail -5 /tmp/sg.err
echo ""
echo "=== Findings ==="
python3 -c "
import json
try:
    with open(\"/tmp/sg.json\") as f:
        d = json.load(f)
    results = d.get(\"results\", [])
    errors = d.get(\"errors\", [])
    print(f\"Findings: {len(results)}\")
    print(f\"Errors: {len(errors)}\")
    sev = {}
    for r in results:
        s = r.get(\"extra\", {}).get(\"severity\", \"?\")
        sev[s] = sev.get(s, 0) + 1
    for k, v in sev.items():
        print(f\"  {k}: {v}\")
except Exception as e:
    print(f\"parse error: {e}\")
"
' 2>&1 | tee "$EVID/semgrep.log"
echo ""

# ============================================
# 5. ดึง Evidence
# ============================================
echo "### 5. Extract Evidence ###"
mkdir -p "$EVID/sandbox"
sbx --cloud cp "$SANDBOX:/tmp/sg.json" "$EVID/sandbox/" 2>&1 | tail -1 || true
sbx --cloud cp "$SANDBOX:/tmp/sg.err" "$EVID/sandbox/" 2>&1 | tail -1 || true
echo ""

# ============================================
# 6. สรุป
# ============================================
echo "============================================"
echo " สรุป"
echo "============================================"
log "Evidence: $EVID"
echo ""
echo "### Results ###"
echo ""
echo "--- Pytest ---"
grep -oE '[0-9]+ (passed|failed|skipped)' "$EVID/pytest.log" 2>/dev/null | tail -5 | tr '\n' ' '
echo ""
echo ""
echo "--- Semgrep ---"
grep -E 'Findings:|Errors:' "$EVID/semgrep.log" 2>/dev/null | tr '\n' ' '
echo ""
echo ""
echo "### Files ###"
ls -la "$EVID/"
echo ""
echo "### Sandbox Status ###"
sbx --cloud ls 2>&1 | tail -6
echo ""

# Archive
cd /root/evidence
tar czf "$EVID.tar.gz" "q10-fix-$TS" 2>/dev/null
log "Archive: $EVID.tar.gz"
sha256sum "$EVID.tar.gz" 2>/dev/null
echo ""
warn "Q10: PARTIAL — ต้อง review"
warn "Production: NO-GO"
echo "============================================"
