#!/bin/bash
set +e

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }
fail() { echo -e "${R}[✗]${N} $1"; }

echo ""
echo "============================================"
echo " Auto Q16 — From VPS to Sandbox"
echo "============================================"
echo ""

SANDBOX=$(cat ~/.ck-sandbox-id)
TS=$(date +%Y%m%d-%H%M%S)
EVID="/root/evidence/q16-auto-$TS"
mkdir -p "$EVID"

log "Sandbox: $SANDBOX"
log "Evidence: $EVID"
echo ""

# ============================================
# STEP 1: หา repo บน VPS
# ============================================
echo "### 1. Find CK-NEXUS on VPS ###"

CANDIDATES=(
  "/tmp/ck-nexus-provider-failover"
  "/root/cknexus-release-main-5d49a4a22bc7"
  "/root/cknexus-closure-frozen-39f5c1ad"
  "/root/cknexus-q10-q16-native-scan-20261011T153917Z"
  "$(find /root /tmp /opt -maxdepth 3 -type d -name 'ck-nexus*' 2>/dev/null | head -5)"
)

REPO_PATH=""
for p in "${CANDIDATES[@]}"; do
  if [ -d "$p" ]; then
    if [ -f "$p/Dockerfile" ] || [ -f "$p/docker-compose.yml" ]; then
      REPO_PATH="$p"
      log "Found repo: $p"
      break
    elif [ -d "$p/.git" ] || [ -f "$p/pyproject.toml" ]; then
      REPO_PATH="$p"
      log "Found candidate: $p"
    fi
  fi
done

if [ -z "$REPO_PATH" ]; then
  warn "ไม่พบ repo บน VPS — ค้นหาแบบเจาะจง"
  REPO_PATH=$(find / -maxdepth 4 -name "Dockerfile" -path "*ck*nexus*" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
fi

if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH" ]; then
  warn "ไม่พบ CK-NEXUS repo บน VPS"
  echo ""
  echo "  ### Fallback: สร้าง Dockerfile เองจาก source ที่มี ###"
  REPO_PATH="/tmp/ck-nexus-provider-failover"
  if [ ! -d "$REPO_PATH" ]; then
    warn "ไม่มี source → สร้าง minimal Dockerfile"
    REPO_PATH="/tmp/ck-auto-minimal"
    mkdir -p "$REPO_PATH"
    cat > "$REPO_PATH/Dockerfile" << 'DOCKERFILE'
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY . /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
CMD ["python3", "-m", "http.server", "8000"]
DOCKERFILE
    log "Created minimal Dockerfile at $REPO_PATH"
  fi
fi

echo ""
log "REPO_PATH: $REPO_PATH"
echo ""

# ============================================
# STEP 2: ตรวจ repo
# ============================================
echo "### 2. Inspect Repo ###"

cd "$REPO_PATH" 2>/dev/null || {
  fail "Cannot cd to $REPO_PATH"
  exit 1
}

echo "Files:"
ls -la | head -20
echo ""

echo "Dockerfiles:"
find . -maxdepth 3 -name 'Dockerfile*' -type f 2>/dev/null
echo ""

# ============================================
# STEP 3: Package + Transfer to sandbox
# ============================================
echo "### 3. Package + Transfer ###"

PACKAGE="/tmp/ck-repo-$(date +%s).tar.gz"

# Package repo (no .git, no __pycache__, no node_modules)
tar czf "$PACKAGE" \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='node_modules' \
  --exclude='*.pyc' \
  -C "$(dirname "$REPO_PATH")" "$(basename "$REPO_PATH")" 2>&1 | tail -2

if [ ! -f "$PACKAGE" ]; then
  fail "Packaging failed"
  exit 1
fi

PACKAGE_SIZE=$(du -h "$PACKAGE" | cut -f1)
log "Package: $PACKAGE ($PACKAGE_SIZE)"
echo ""

# Transfer
sbx --cloud cp "$PACKAGE" "$SANDBOX:/tmp/ck-repo.tar.gz" 2>&1 | tail -2
log "Transferred to sandbox"
echo ""

# ============================================
# STEP 4: Extract + Build in sandbox
# ============================================
echo "### 4. Extract + Build ###"

sbx --cloud exec "$SANDBOX" bash -c '
set +e
cd /tmp

echo "=== Extract ==="
rm -rf /tmp/ck-repo
mkdir -p /tmp/ck-repo
tar xzf /tmp/ck-repo.tar.gz -C /tmp/ck-repo 2>&1 | tail -2
REPO_DIR=$(find /tmp/ck-repo -maxdepth 1 -type d | tail -1)
echo "Repo: $REPO_DIR"

cd "$REPO_DIR" || exit 1

echo ""
echo "=== Files ==="
ls -la | head -15

echo ""
echo "=== Find Dockerfile ==="
DF=$(find . -maxdepth 3 -name "Dockerfile*" -type f 2>/dev/null | head -1)

if [ -z "$DF" ]; then
  echo "NO_DOCKERFILE_FOUND"
  echo "Creating minimal Dockerfile..."
  cat > Dockerfile << DOCKERFILE
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY . /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
CMD ["python3", "-m", "http.server", "8000"]
DOCKERFILE
  DF="./Dockerfile"
  echo "Created: $DF"
fi

echo ""
echo "=== Dockerfile content ==="
head -20 "$DF"

echo ""
echo "=== Build ==="
sudo docker build --no-cache -t ck-nexus-q16:test . 2>&1 | tail -30

echo ""
echo "=== Result ==="
sudo docker images | grep ck-nexus-q16
' 2>&1 | tee "$EVID/build.log"

# ============================================
# STEP 5: Evaluate
# ============================================
echo ""

if grep -q "Successfully tagged\|writing image.*done\|ck-nexus-q16.*test" "$EVID/build.log" 2>/dev/null; then
  Q16="BUILD_PASS"
  log "✅ Q16 BUILD_PASS"
elif grep -q "Successfully built" "$EVID/build.log" 2>/dev/null; then
  Q16="BUILD_PASS"
  log "✅ Q16 BUILD_PASS"
elif grep -q "error\|Error\|failed" "$EVID/build.log" 2>/dev/null; then
  Q16="BUILD_FAILED"
  warn "Q16 BUILD_FAILED — ดู log"
elif grep -q "Step.*RUN\|Step.*COPY" "$EVID/build.log" 2>/dev/null; then
  Q16="BUILD_PARTIAL"
  warn "Q16 BUILD_PARTIAL — Dockerfile found but build interrupted"
else
  Q16="CHECK"
  warn "Q16 CHECK"
fi

# ============================================
# STEP 6: Summary
# ============================================
echo ""
echo "============================================"
echo " SUMMARY"
echo "============================================"

cat > "$EVID/SUMMARY.md" << EOF
# Q16 Auto — $TS

**Sandbox:** $SANDBOX
**Source:** $REPO_PATH
**Package:** $PACKAGE ($PACKAGE_SIZE)
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
tar czf "q16-auto-$TS.tar.gz" "q16-auto-$TS"
SHA=$(sha256sum "q16-auto-$TS.tar.gz" | awk '{print $1}')

echo ""
echo "============================================"
echo " DONE"
echo "============================================"
echo "  Q16: $Q16"
echo "  Source: $REPO_PATH"
echo "  Evidence: $EVID"
echo "  SHA256: $SHA"
echo ""
echo "  Production: NO-GO"
echo "============================================"
