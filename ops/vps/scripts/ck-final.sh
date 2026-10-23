#!/bin/bash
set -o pipefail
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

SANDBOX="sbx_001m4w3j1z26691b5t5xxpxmbh1"
TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q10-final-$TS"
mkdir -p "$EVID"

echo ""
echo "============================================"
echo " CK-NEXUS Q10 — Environment Fix + Run"
echo "============================================"
echo ""

# 1. หา test env ที่ต้องใช้
echo "### 1. Discover Test Env ###"
sbx --cloud exec "$SANDBOX" bash -c '
cd ~/work/ck-nexus 2>/dev/null || exit 1
echo "=== conftest.py ==="
cat tests/conftest.py 2>/dev/null | head -40
echo ""
echo "=== pytest.ini / pyproject.toml [tool.pytest] ==="
grep -A20 "tool.pytest\|\[pytest\]" pytest.ini pyproject.toml setup.cfg 2>/dev/null | head -30
echo ""
echo "=== ENV vars expected by tests ==="
grep -rn "os.environ\|getenv\|OMNI_CONTEXT\|CKNEXUS_ACCESS" tests/ 2>/dev/null | head -20
' 2>&1 | tee "$EVID/test-env-discovery.log"
echo ""

# 2. รัน pytest with proper env
echo "### 2. Pytest with Test Env ###"
warn "ใช้เวลา 30-60 วินาที"
echo ""
sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/work/ck-nexus 2>/dev/null || exit 1

# ล้าง env ที่รบกวน
unset OPENAI_API_KEY 2>/dev/null
unset CKNEXUS_ACCESS_TOKEN 2>/dev/null
unset OMNI_CONTEXT 2>/dev/null

# set test env
export CKNEXUS_TEST_MODE=1
export PYTHONPATH=.

python3 -m pytest tests/ -v --tb=line -p no:warnings 2>&1 | tail -40
' 2>&1 | tee "$EVID/pytest-clean.log"
echo ""

# 3. รัน pytest เฉพาะ test files ที่ผ่าน (baseline)
echo "### 3. Baseline Pytest (Known-Passing) ###"
sbx --cloud exec "$SANDBOX" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/work/ck-nexus 2>/dev/null || exit 1
export PYTHONPATH=.

# test files ที่ไม่ใช่ AGNES
python3 -m pytest tests/ -v --tb=line -p no:warnings \
  --ignore=tests/test_agnes_execution_kernel_phase1.py \
  --ignore=tests/test_agnes_execution_kernel_phase2.py \
  --ignore=tests/test_agnes_execution_kernel_phase3.py \
  --ignore=tests/test_agnes_skill_nervous_system.py \
  --ignore=tests/test_creator_api.py \
  2>&1 | tail -20
' 2>&1 | tee "$EVID/pytest-baseline.log"
echo ""

# 4. วิเคราะห์ Semgrep 12 errors
echo "### 4. Semgrep Errors Analysis ###"
sbx --cloud exec "$SANDBOX" bash -c '
python3 << "PYEOF"
import json
with open("/tmp/sg.json") as f:
    d = json.load(f)

errors = d.get("errors", [])
print(f"=== {len(errors)} Semgrep Errors ===")
for e in errors[:15]:
    path = e.get("path", "?")
    msg = e.get("message", "?")[:80]
    typ = e.get("type", "?")
    print(f"  [{typ}] {path}")
    print(f"    {msg}")

print()
print("=== ERROR severity findings ===")
for r in d.get("results", []):
    sev = r.get("extra", {}).get("severity", "")
    if sev == "ERROR":
        path = r.get("path", "?")
        line = r.get("start", {}).get("line", "?")
        check = r.get("check_id", "?").split(".")[-1]
        print(f"  {path}:{line} — {check}")
PYEOF
' 2>&1 | tee "$EVID/semgrep-errors.log"
echo ""

# 5. สรุป
echo "============================================"
echo " สรุป"
echo "============================================"
log "Evidence: $EVID"
echo ""

echo "### Pytest (clean env) ###"
grep -E "passed|failed|error" "$EVID/pytest-clean.log" 2>/dev/null | tail -1

echo ""
echo "### Pytest (baseline, no AGNES) ###"
grep -E "passed|failed|error" "$EVID/pytest-baseline.log" 2>/dev/null | tail -1

echo ""
echo "### Semgrep Errors ###"
head -20 "$EVID/semgrep-errors.log" 2>/dev/null

echo ""
cd /root/evidence
tar czf "$EVID.tar.gz" "q10-final-$TS" 2>/dev/null
sha256sum "$EVID.tar.gz" 2>/dev/null
echo ""
warn "Q10: PARTIAL — ต้อง review"
warn "Production: NO-GO"
echo "============================================"
