#!/bin/bash
set +e

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[✗]${N} $1"; }

echo ""
echo "============================================"
echo " Q16 — Token Diagnostic"
echo "============================================"
echo ""

SANDBOX=$(cat ~/.ck-sandbox-id)

# ถาม token ใหม่ (จะใช้ตัวเก่าหรือใหม่ก็ได้)
read -rsp "🔑 GitHub PAT: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
  fail "ไม่มี token"
  exit 1
fi

echo "  Token: ${GITHUB_TOKEN:0:10}...${GITHUB_TOKEN: -4}"
echo ""

# ============================================
# Test 1: Token identity
# ============================================
echo "### Test 1: Token Identity ###"

sbx --cloud exec "$SANDBOX" bash -c "
curl -s -H 'Authorization: Bearer $GITHUB_TOKEN' \
  https://api.github.com/user | \
  python3 -c 'import json,sys; d=json.load(sys.stdin); print(\"User:\", d.get(\"login\", \"?\"), \"| Type:\", d.get(\"type\", \"?\"))' 2>&1 || echo 'API call failed'
"
echo ""

# ============================================
# Test 2: Repo access
# ============================================
echo "### Test 2: Repo Access ###"

for REPO in "CK-NEXUS-AI/ck-nexus" "spinlnw10-art/ck-nexus"; do
  echo "  Checking $REPO..."
  RESULT=$(sbx --cloud exec "$SANDBOX" bash -c "
curl -s -o /dev/null -w '%{http_code}' \
  -H 'Authorization: Bearer $GITHUB_TOKEN' \
  https://api.github.com/repos/$REPO
")
  echo "    HTTP: $RESULT"

  if [ "$RESULT" = "200" ]; then
    log "  ✓ $REPO accessible"
    WORKING_REPO="$REPO"
    break
  else
    warn "  ✗ $REPO — HTTP $RESULT"
  fi
done
echo ""

if [ -z "$WORKING_REPO" ]; then
  fail "ไม่มี repo ที่เข้าถึงได้"
  echo ""
  echo "  ### แก้ไข:"
  echo "  1. เปิด https://github.com/settings/tokens"
  echo "  2. ลบ token เก่า → สร้างใหม่"
  echo "  3. Classic: เลือก scope 'repo' (full)"
  echo "  4. Fine-grained: Repository access → เลือก CK-NEXUS-AI/ck-nexus"
  echo "  5. ถ้า org → authorize SSO"
  exit 1
fi

echo "### Using repo: $WORKING_REPO ###"
echo ""

# ============================================
# Test 3: Clone
# ============================================
echo "### Test 3: Clone ###"

sbx --cloud exec "$SANDBOX" bash -c "
cd ~/work 2>/dev/null || mkdir -p ~/work && cd ~/work
rm -rf ck-nexus 2>/dev/null

git clone --depth 1 https://oauth2:$GITHUB_TOKEN@github.com/$WORKING_REPO.git 2>&1 | tail -5

cd ck-nexus 2>/dev/null && {
  echo ''
  echo 'Files:' \$(ls | wc -l)
  echo ''
  echo '=== Dockerfiles ==='
  find . -maxdepth 3 -name 'Dockerfile*' -type f 2>/dev/null | head -5
}
" 2>&1 | tee /tmp/q16-clone.log
echo ""

# ============================================
# Test 4: Docker build
# ============================================
echo "### Test 4: Docker Build ###"

sbx --cloud exec "$SANDBOX" bash -c "
cd ~/work/ck-nexus 2>/dev/null || { echo 'NO_REPO'; exit 0; }

DF=\$(find . -maxdepth 2 -name 'Dockerfile*' -type f 2>/dev/null | head -1)
[ -z \"\$DF\" ] && { echo 'NO_DOCKERFILE'; exit 0; }

echo \"Found: \$DF\"
echo ''
echo '=== Content (first 15 lines) ==='
head -15 \"\$DF\"
echo ''
echo '=== Build ==='
sudo docker build --no-cache -t ck-nexus-q16:test . 2>&1 | tail -25
" 2>&1 | tee /tmp/q16-build.log
echo ""

# ============================================
# Result
# ============================================
if grep -q "Successfully built\|writing image" /tmp/q16-build.log; then
  RESULT="BUILD_PASS"
elif grep -q "FROM " /tmp/q16-build.log; then
  RESULT="DOCKERFILE_FOUND"
elif grep -q "NO_DOCKERFILE" /tmp/q16-build.log; then
  RESULT="NO_DOCKERFILE"
elif grep -q "NO_REPO" /tmp/q16-build.log; then
  RESULT="CLONE_FAILED"
else
  RESULT="CHECK"
fi

echo "============================================"
echo " Q16 RESULT: $RESULT"
echo "============================================"
echo ""
log "Repo: $WORKING_REPO"
log "Clone log: /tmp/q16-clone.log"
log "Build log: /tmp/q16-build.log"
echo ""

echo "### Diagnosis ###"
case $RESULT in
  BUILD_PASS)
    log "✅ Docker build สำเร็จ — Q16 PASS"
    ;;
  DOCKERFILE_FOUND)
    warn "Dockerfile มี แต่ build ไม่จบ — ดู log"
    tail -20 /tmp/q16-build.log
    ;;
  NO_DOCKERFILE)
    warn "Repo clone ได้ แต่ไม่มี Dockerfile"
    ;;
  CLONE_FAILED)
    fail "Clone ยัง fail — token ยังมีปัญหา"
    ;;
  *)
    warn "ตรวจสอบ log"
    ;;
esac
echo "============================================"
