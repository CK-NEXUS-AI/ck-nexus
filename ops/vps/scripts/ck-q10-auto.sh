#!/bin/bash
set -o pipefail

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

SANDBOX_ID="sbx_001m4w3j1z26691b5t5xxpxmbh1"
TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q10-auto-$TS"
mkdir -p "$EVID"/{scans,tests}

echo "============================================"
echo " CK-NEXUS Q10 Auto"
echo "============================================"
log "Sandbox: $SANDBOX_ID"
log "Evidence: $EVID"
echo ""

# Phase 1: Sandbox list
echo "### Phase 1: Sandbox List ###"
sbx --cloud ls | tee "$EVID/sandbox-list.txt"
echo ""

# Phase 2: TTL + Stop unused
echo "### Phase 2: TTL + Stop ###"
sbx --cloud ttl "$SANDBOX_ID" --extend 12h 2>&1 | tail -2
sbx --cloud stop ck-q10-1791939590 2>&1 | tail -1
sbx --cloud stop mvbejb 2>&1 | tail -1
echo ""

# Phase 3: Env check
echo "### Phase 3: Env Check ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
echo "OPENAI: $(env | grep -c OPENAI 2>/dev/null)"
echo "GITHUB: $(env | grep -c GITHUB 2>/dev/null)"
echo "python:  $(command -v python 2>/dev/null || echo NOT_FOUND)"
echo "python3: $(command -v python3 2>/dev/null || echo NOT_FOUND)"
' 2>&1 | tee "$EVID/env-check.log"
echo ""

# Phase 4: Fix python symlink
echo "### Phase 4: Fix python ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
mkdir -p ~/.local/bin
command -v python >/dev/null 2>&1 || ln -sf $(command -v python3) ~/.local/bin/python
export PATH="$HOME/.local/bin:$PATH"
which python && python --version
' 2>&1 | tee "$EVID/python-fix.log"
echo ""

# Phase 5: omni_context
echo "### Phase 5: omni_context ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
cd ~/work/ck-nexus 2>/dev/null || cd ~/ck-nexus 2>/dev/null || cd /tmp/ck-nexus 2>/dev/null || exit 0
grep -rn "omni_context" tests/ 2>/dev/null | head -10 || echo "not found"
' 2>&1 | tee "$EVID/omni-context.log"
echo ""

# Phase 6: Pytest
echo "### Phase 6: Pytest ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
export PATH="$HOME/.local/bin:$PATH"
cd ~/work/ck-nexus 2>/dev/null || cd ~/ck-nexus 2>/dev/null || exit 0
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -40
' 2>&1 | tee "$EVID/tests/pytest.log"
echo ""

# Phase 7: Semgrep
echo "### Phase 7: Semgrep ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
cd ~/work/ck-nexus 2>/dev/null || exit 0
python3 -m venv /tmp/sg 2>/dev/null
source /tmp/sg/bin/activate
pip install --quiet semgrep 2>&1 | tail -1
semgrep scan --config=auto --json . > /tmp/sg.json 2>&1
echo "exit: $?"
wc -c /tmp/sg.json
' 2>&1 | tee "$EVID/scans/semgrep.log"
echo ""

# Phase 8: Gitleaks context
echo "### Phase 8: Gitleaks ###"
sbx --cloud exec "$SANDBOX_ID" bash -c '
cd ~/work/ck-nexus 2>/dev/null || exit 0
[ -f .env.example ] && sed -n "45,55p" .env.example | sed "s/=.*/= <REDACTED>/" || echo "no .env.example"
' 2>&1 | tee "$EVID/scans/gitleaks.log"
echo ""

# Phase 9: Summary
echo "============================================"
echo " Summary"
echo "============================================"
log "Evidence: $EVID"
echo ""
echo "### Files ###"
find "$EVID" -type f | head -20
echo ""
warn "Q10: PARTIAL"
warn "Production: NO-GO"
echo "============================================"
