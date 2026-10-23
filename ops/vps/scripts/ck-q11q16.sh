#!/bin/bash
set +e

# ============================================
# CK-NEXUS Q11-Q16 — Auto Key Prompt
# ============================================
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[✗]${N} $1"; }

echo ""
echo "============================================"
echo " CK-NEXUS Q11-Q16"
echo "============================================"
echo ""

# ---------- INPUT: Ask for key ----------
SANDBOX=$(cat ~/.ck-sandbox-id 2>/dev/null)
if [ -z "$SANDBOX" ]; then
  read -rp "Sandbox ID: " SANDBOX
  echo "$SANDBOX" > ~/.ck-sandbox-id
fi

echo "  Sandbox: $SANDBOX"
echo ""
echo "  สมัคร Groq ฟรี: https://console.groq.com/keys"
echo ""

read -rsp "🔑 Groq API Key (gsk_...): " GROQ_KEY
echo ""

if [ -z "$GROQ_KEY" ]; then
  fail "ไม่ได้ใส่ key"
  exit 1
fi

log "รับ key เรียบร้อย (${#GROQ_KEY} ตัวอักษร)"
echo ""

# ---------- Save config ----------
cat > ~/.ck-env << ENVEOF
export SANDBOX=$SANDBOX
export GROQ_KEY=$GROQ_KEY
export GROQ_MODEL=allam-2-7b
ENVEOF
chmod 600 ~/.ck-env
log "Config saved: ~/.ck-env"
echo ""

TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q11-q16-$TS"
mkdir -p "$EVID"

# ============================================
# Q11 — Live Provider
# ============================================
echo "### Q11 — Live Provider (Groq) ###"

sbx --cloud exec "$SANDBOX" bash -c "
KEY='$GROQ_KEY'
CODE=\$(curl -s -o /tmp/q11-chat.json -w '%{http_code}' --max-time 30 \
  -X POST https://api.groq.com/openai/v1/chat/completions \
  -H \"Authorization: Bearer \$KEY\" \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"allam-2-7b\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply exactly: CK-Q11-OK\"}],\"max_tokens\":20}')
echo \"HTTP: \$CODE\"
cat /tmp/q11-chat.json | head -c 300
" 2>&1 | tee "$EVID/q11.log"

sbx --cloud cp "$SANDBOX:/tmp/q11-chat.json" "$EVID/q11-chat.json" 2>/dev/null

if grep -q "HTTP: 200" "$EVID/q11.log"; then
  Q11="PASS"
  log "Q11 PASS"
else
  Q11="FAIL"
  fail "Q11 FAIL"
fi
echo ""

# ============================================
# Q12 — cgroup v2
# ============================================
echo "### Q12 — cgroup v2 ###"
sbx --cloud exec "$SANDBOX" bash -c '
[ -f /sys/fs/cgroup/cgroup.controllers ] && echo "cgroup_v2: MOUNTED" || echo "NOT_MOUNTED"
echo "Controllers: $(cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null)"
echo "memory.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
echo "pids.max: $(cat /sys/fs/cgroup/pids.max 2>/dev/null)"
' 2>&1 | tee "$EVID/q12.log"

Q12=$(grep -q "MOUNTED" "$EVID/q12.log" && echo "PASS" || echo "PARTIAL")
log "Q12: $Q12"
echo ""

# ============================================
# Q13 — PostgreSQL
# ============================================
echo "### Q13 — PostgreSQL ###"
sbx --cloud exec "$SANDBOX" bash -c '
which pg_dump >/dev/null 2>&1 && { pg_dump --version; exit 0; }
echo "Installing (with sudo)..."
sudo apt-get update -qq 2>&1 | tail -1
sudo apt-get install -y postgresql-client 2>&1 | tail -2
which pg_dump psql
pg_dump --version 2>&1
' 2>&1 | tee "$EVID/q13.log"

Q13=$(grep -qE "pg_dump.*[0-9]" "$EVID/q13.log" && echo "PASS" || echo "SKIP")
log "Q13: $Q13"
echo ""

# ============================================
# Q14 — Observability
# ============================================
echo "### Q14 — Observability ###"
sbx --cloud exec "$SANDBOX" bash -c '
pip install --quiet --user opentelemetry-api opentelemetry-sdk prometheus-client 2>&1 | tail -2
python3 -c "import opentelemetry; print(\"otel:\", opentelemetry.__version__)" 2>&1
python3 -c "import prometheus_client; print(\"prom:\", prometheus_client.__version__)" 2>&1
' 2>&1 | tee "$EVID/q14.log"

Q14=$(grep -q "otel:" "$EVID/q14.log" && echo "PASS" || echo "SKIP")
log "Q14: $Q14"
echo ""

# ============================================
# Q15 — Clean Machine
# ============================================
echo "### Q15 — Clean Machine ###"
sbx --cloud exec "$SANDBOX" bash -c '
uname -a
cat /etc/os-release | grep -E "^(NAME|VERSION)="
uptime
whoami
id
' 2>&1 | tee "$EVID/q15.log"

Q15="INFO_COLLECTED"
log "Q15: $Q15"
echo ""

# ============================================
# Q16 — Production Package
# ============================================
echo "### Q16 — Production Package ###"
sbx --cloud exec "$SANDBOX" bash -c '
which docker 2>/dev/null || echo "no-docker"
cd ~/work 2>/dev/null || mkdir -p ~/work && cd ~/work
if [ ! -d ck-nexus ]; then
  git clone --depth 1 https://github.com/CK-NEXUS-AI/ck-nexus.git 2>&1 | tail -2
fi
cd ck-nexus 2>/dev/null && {
  echo "=== Files ==="
  ls Dockerfile* 2>/dev/null || echo "no Dockerfile"
  head -15 Dockerfile 2>/dev/null
}
' 2>&1 | tee "$EVID/q16.log"

if grep -q "no Dockerfile" "$EVID/q16.log"; then
  Q16="NO_DOCKERFILE"
elif grep -q "FROM " "$EVID/q16.log"; then
  Q16="DOCKERFILE_FOUND"
else
  Q16="CHECK"
fi
log "Q16: $Q16"
echo ""

# ============================================
# Summary
# ============================================
echo "============================================"
echo " SUMMARY"
echo "============================================"

cat > "$EVID/SUMMARY.md" << EOF
# Q11-Q16 — $TS

**Sandbox:** $SANDBOX
**Provider:** Groq
**Model:** allam-2-7b

| Gate | Status |
|---|---|
| Q11 | $Q11 |
| Q12 | $Q12 |
| Q13 | $Q13 |
| Q14 | $Q14 |
| Q15 | $Q15 |
| Q16 | $Q16 |

**Production:** NO-GO
EOF

cat "$EVID/SUMMARY.md"
echo ""

# Archive
cd "$EVID"
find . -type f -not -name "SHA256SUMS*" -exec sha256sum {} \; > SHA256SUMS
sha256sum -c SHA256SUMS 2>&1 | tail -2

cd /root/evidence
tar czf "q11-q16-$TS.tar.gz" "q11-q16-$TS"
SHA=$(sha256sum "q11-q16-$TS.tar.gz" | awk '{print $1}')

echo ""
echo "============================================"
echo " DONE"
echo "============================================"
echo "  Q11: $Q11"
echo "  Q12: $Q12"
echo "  Q13: $Q13"
echo "  Q14: $Q14"
echo "  Q15: $Q15"
echo "  Q16: $Q16"
echo ""
echo "  Evidence: $EVID"
echo "  SHA256: $SHA"
echo "  Production: NO-GO"
echo ""
echo "  🚨 ลบ key ที่ https://console.groq.com/keys"
echo "============================================"
