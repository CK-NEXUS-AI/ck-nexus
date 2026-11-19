#!/bin/bash
set -o pipefail
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

SANDBOX="sbx_001m4w3j1z26691b5t5xxpxmbh1"
TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q10-run-$TS"
mkdir -p "$EVID"

echo ""
echo "============================================"
echo " CK-NEXUS Q10 — TTL + Install + Run"
echo "============================================"
echo ""

# 1. TTL — syntax ถูก: +DURATION ก่อน SANDBOX_ID
echo "### 1. TTL Extend ###"
sbx --cloud ttl +12h "$SANDBOX" 2>&1 | tail -3
echo ""

# 2. ติดตั้ง dependencies ครบ + pytest + semgrep
echo "### 2. Install All Dependencies ###"
warn "ใช้เวลา 3-5 นาที"
echo ""
sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/ck-nexus 2>/dev/null || cd ~/work/ck-nexus 2>/dev/null || cd /workspace 2>/dev/null || exit 1
echo "=== Working dir: $(pwd) ==="
echo ""
echo "=== Install requirements ==="
python3 -m pip install --break-system-packages --quiet -r requirements.txt 2>&1 | tail -3
python3 -m pip install --break-system-packages --quiet -r requirements-dev.txt 2>&1 | tail -3
echo ""
echo "=== Install test tools ==="
python3 -m pip install --break-system-packages --quiet pytest pytest-asyncio semgrep 2>&1 | tail -3
echo ""
echo "=== Verify ==="
python3 -c "import fastapi, sqlalchemy; print(\"fastapi+sqlalchemy OK\")" 2>&1
pytest --version 2>&1 | head -1
semgrep --version 2>&1 | head -1
' 2>&1 | tee "$EVID/install.log"
echo ""

# 3. รัน Pytest
echo "### 3. Run Pytest ###"
warn "ใช้เวลา 60-120 วินาที"
echo ""
sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/ck-nexus 2>/dev/null || cd ~/work/ck-nexus 2>/dev/null || exit 1
python3 -m pytest tests/ -v --tb=short -p no:warnings 2>&1 | tail -60
' 2>&1 | tee "$EVID/pytest.log"
echo ""

# 4. รัน Semgrep (ใช้ semgrep ตรง ไม่ผ่าน python -m)
echo "### 4. Run Semgrep ###"
warn "ใช้เวลา 60-120 วินาที"
echo ""
sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/ck-nexus 2>/dev/null || cd ~/work/ck-nexus 2>/dev/null || exit 1
semgrep scan --config=auto --json --quiet . > /tmp/sg.json 2>/tmp/sg.err
echo "exit: $?"
echo "size: $(wc -c < /tmp/sg.json) bytes"
echo ""
echo "=== Findings Summary ==="
python3 -c "
import json
with open(\"/tmp/sg.json\") as f: d = json.load(f)
results = d.get(\"results\", [])
errors = d.get(\"errors\", [])
print(f\"Findings: {len(results)}\")
print(f\"Errors: {len(errors)}\")
sev = {}
for r in results:
    s = r.get(\"extra\", {}).get(\"severity\", \"?\")
    sev[s] = sev.get(s, 0) + 1
for k in sorted(sev.keys()):
    print(f\"  {k}: {sev[k]}\")
" 2>&1
' 2>&1 | tee "$EVID/semgrep.log"
echo ""

# 5. ดึง Evidence
echo "### 5. Extract Evidence ###"
mkdir -p "$EVID/sandbox"
sbx --cloud cp "$SANDBOX:/tmp/sg.json" "$EVID/sandbox/" 2>&1 | tail -1
sbx --cloud cp "$SANDBOX:/tmp/sg.err" "$EVID/sandbox/" 2>&1 | tail -1
echo ""

# 6. สรุป
echo "============================================"
echo " สรุป"
echo "============================================"
log "Evidence: $EVID"
echo ""
echo "--- Pytest ---"
grep -E '^[0-9]+ (passed|failed|error|skipped)|passed|failed|error' "$EVID/pytest.log" 2>/dev/null | tail -3
echo ""
echo "--- Semgrep ---"
grep -E 'Findings:|Errors:' "$EVID/semgrep.log" 2>/dev/null
echo ""
echo "--- TTL ---"
sbx --cloud ttl "$SANDBOX" 2>&1 | tail -3
echo ""

cd /root/evidence
tar czf "$EVID.tar.gz" "q10-run-$TS" 2>/dev/null
sha256sum "$EVID.tar.gz" 2>/dev/null
echo ""
warn "Q10: PARTIAL — ต้อง review"
warn "Production: NO-GO"
echo "============================================"
