#!/bin/bash
set +e

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[✗]${N} $1"; }

echo ""
echo "============================================"
echo " CK-NEXUS Q16 — Docker Build"
echo "============================================"
echo ""

SANDBOX=$(cat ~/.ck-sandbox-id 2>/dev/null)
if [ -z "$SANDBOX" ]; then
  read -rp "Sandbox ID: " SANDBOX
  echo "$SANDBOX" > ~/.ck-sandbox-id
fi

echo "  Sandbox: $SANDBOX"
echo ""
echo "  สร้าง GitHub PAT: https://github.com/settings/tokens"
echo "  Scope: repo (Classic) หรือ Contents: Read (Fine-grained)"
echo ""

read -rsp "🔑 GitHub PAT (ghp_... หรือ github_pat_...): " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
  fail "ไม่ได้ใส่ token"
  exit 1
fi

log "รับ token เรียบร้อย (${#GITHUB_TOKEN} ตัวอักษร)"
echo ""

# Save token (protected)
cat > ~/.gh-token << GHTOKEN
$GITHUB_TOKEN
GHTOKEN
chmod 600 ~/.gh-token
log "Token saved: ~/.gh-token"
echo ""

TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q16-$TS"
mkdir -p "$EVID"

# ============================================
# Clone repo with token
# ============================================
echo "### Clone CK-NEXUS ###"

sbx --cloud exec "$SANDBOX" bash -c "
set +e
TOKEN='$GITHUB_TOKEN'

echo '=== Clean old ==='
rm -rf ~/work/ck-nexus 2>/dev/null
mkdir -p ~/work
cd ~/work

echo '=== Clone with token ==='
git clone --depth 1 https://oauth2:\${TOKEN}@github.com/CK-NEXUS-AI/ck-nexus.git 2>&1 | tail -3
RC=\$?

if [ \$RC -ne 0 ]; then
  echo ''
  echo '=== Try alt repo: spinlnw10-art ==='
  git clone --depth 1 https://oauth2:\${TOKEN}@github.com/spinlnw10-art/ck-nexus.git 2>&1 | tail -3
fi

echo ''
echo '=== Verify ==='
cd ~/work/ck-nexus 2>/dev/null && {
  echo \"Cloned: \$(pwd)\"
  echo \"Files: \$(ls | wc -l)\"
  echo ''
  echo '=== Dockerfile check ==='
  ls -la Dockerfile* 2>/dev/null || echo 'no Dockerfile in root'
  echo ''
  echo '=== Find all Dockerfiles ==='
  find . -maxdepth 3 -name 'Dockerfile*' -type f 2>/dev/null | head -10
}
" 2>&1 | tee "$EVID/clone.log"

echo ""

# ============================================
# Docker Build
# ============================================
echo "### Q16 — Docker Build ###"

sbx --cloud exec "$SANDBOX" bash -c "
cd ~/work/ck-nexus 2>/dev/null || exit 0

echo '=== Docker version ==='
docker --version

echo ''
echo '=== Find Dockerfile ==='
DF=\$(find . -maxdepth 2 -name 'Dockerfile*' -type f 2>/dev/null | head -1)

if [ -z \"\$DF\" ]; then
  echo 'NO_DOCKERFILE'
  exit 0
fi

echo \"Found: \$DF\"
echo ''
echo '=== Dockerfile content (first 20 lines) ==='
head -20 \"\$DF\"
echo ''
echo '=== Build (with sudo) ==='
sudo docker build --no-cache -t ck-nexus-q16:test . 2>&1 | tail -25
" 2>&1 | tee "$EVID/build.log"

# ============================================
# Evaluate
# ============================================
if grep -q "Successfully built\|Successfully tagged\|writing image" "$EVID/build.log" 2>/dev/null; then
  Q16="BUILD_PASS"
  log "Q16 PASS — Docker image built"
elif grep -q "FROM " "$EVID/build.log" 2>/dev/null; then
  Q16="DOCKERFILE_FOUND"
  warn "Q16 — Dockerfile found but build incomplete"
elif grep -q "NO_DOCKERFILE" "$EVID/build.log" 2>/dev/null; then
  Q16="NO_DOCKERFILE"
  warn "Q16 — Repo cloned but no Dockerfile"
else
  Q16="CHECK"
  warn "Q16 — Check logs"
fi
echo ""

# ============================================
# Summary
# ============================================
echo "============================================"
echo " SUMMARY"
echo "============================================"

cat > "$EVID/SUMMARY.md" << EOF
# Q16 — Docker Build Test — $TS

**Sandbox:** $SANDBOX
**Repo:** CK-NEXUS-AI/ck-nexus
**Status:** $Q16

## Files
$(ls "$EVID" 2>/dev/null | sed 's|^|- |')

**Production:** NO-GO
EOF

cat "$EVID/SUMMARY.md"
echo ""

cd "$EVID"
find . -type f -not -name "SHA256SUMS*" -exec sha256sum {} \; > SHA256SUMS
sha256sum -c SHA256SUMS 2>&1 | tail -2

cd /root/evidence
tar czf "q16-$TS.tar.gz" "q16-$TS"
SHA=$(sha256sum "q16-$TS.tar.gz" | awk '{print $1}')

echo ""
echo "============================================"
echo " DONE"
echo "============================================"
echo "  Q16: $Q16"
echo "  Evidence: $EVID"
echo "  SHA256: $SHA"
echo ""
echo "  Production: NO-GO"
echo ""
echo "  🚨 เก็บ token ไว้ที่ ~/.gh-token (chmod 600)"
echo "     ลบหรือ rotate หลังใช้เสร็จ"
echo "============================================"
