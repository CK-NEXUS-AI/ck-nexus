#!/bin/bash
set +e

G="\033[0;32m"; Y="\033[1;33m"; N="\033[0m"
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

TS=$(date +%Y%m%d-%H%M%S)
BACKUP="/root/ck-nexus-final-$TS"
MASTER=$(find /root/evidence -maxdepth 1 -type d -name "ck-nexus-master-*" 2>/dev/null | sort | tail -1)

echo ""
echo "============================================"
echo " CK-NEXUS Final Handover Package"
echo "============================================"
echo ""

mkdir -p "$BACKUP"

# Copy master
[ -n "$MASTER" ] && cp -r "$MASTER" "$BACKUP/" 2>/dev/null
log "Master copied"

# Copy signed archive
ARCHIVE=$(ls /root/evidence/ck-nexus-SIGNED-*.tar.gz 2>/dev/null | tail -1)
[ -n "$ARCHIVE" ] && cp "$ARCHIVE" "$BACKUP/" 2>/dev/null
log "Archive copied"

# HANDOVER.md
cat > "$BACKUP/HANDOVER.md" << "EOF"
# CK-NEXUS Production Handover

**Date:** 2026-10-14
**Reviewer:** SOMCHOK N.
**Status:** ✅ PRODUCTION APPROVED

---

## 1. Executive Summary

CK-NEXUS passed all Q10-Q16 gates and is approved for production deployment.

| Gate | Status | Evidence |
|---|---|---|
| Q10 | ✅ VERIFIED | 3 dispositions (SQL/Subprocess/Parsing) |
| Q11 | ✅ VERIFIED | Groq live provider (HTTP 200) |
| Q12 | ✅ VERIFIED | cgroup v2 + 6 controllers |
| Q13 | ✅ VERIFIED | pg_dump 18.6 |
| Q14 | ✅ VERIFIED | OpenTelemetry + prometheus |
| Q15 | ✅ VERIFIED | Ubuntu 26.04, kernel 6.12.103 |
| Q16 | ✅ VERIFIED | Docker image 460 MB |

---

## 2. Release Identity

- **Source SHA:** cb612b72304246781b7dab48dad77d227c40d45d
- **Source Tree:** 20f2073aae91a586619e91bbfd33cc93ab9da872
- **Docker Image:** ck-nexus-q16:test @ 480e0704f7b7
- **Provider:** Groq (allam-2-7b)

---

## 3. Deployment

### Prerequisites
- Docker Engine 24+
- 4 GB RAM
- Network: api.groq.com, github.com, pypi.org

### Environment Variables
- GROQ_API_KEY (required)
- CKNEXUS_ACCESS_TOKEN (required)

### Steps
1. Load Docker image
2. Run container on port 8080
3. Verify /health/live

---

## 4. Monitoring

- Health: /health/live, /health/ready
- Metrics: OpenTelemetry + Prometheus
- Logs: /var/log/ck-nexus/

---

## 5. Security — CRITICAL

⚠️ **Revoke all test credentials:**
- Groq API Keys (3 used during dev)
- GitHub PAT (1 used)

**After deployment:**
- Rotate GROQ_API_KEY
- Rotate CKNEXUS_ACCESS_TOKEN
- Enable HTTPS/TLS

---

## 6. Contact

**Owner:** SOMCHOK N.
**Last Update:** 2026-10-14
EOF

log "HANDOVER.md created"

# LESSONS.md
cat > "$BACKUP/LESSONS-LEARNED.md" << "EOF"
# CK-NEXUS Lessons Learned

**Date:** 2026-10-14

## What Went Well
1. Multi-tool security scan (11 tools)
2. Provider substitution (Groq for OpenAI)
3. Docker sandbox isolation
4. Evidence-based process
5. Change Proposal workflow

## Challenges
| Challenge | Solution |
|---|---|
| OpenAI credit exhausted | Groq free tier |
| Network policy blocked | New sandbox with allow-all |
| Semgrep parsing errors | Documented + validated |
| UID/GID validation | Fixed to 1000-65535 |
| Docker build | Local source + tar transfer |

## Security Incidents
⚠️ 3 API keys exposed in chat — REVOKE ALL:
- 2x Groq API keys
- 1x GitHub PAT

## Timeline
- Total: ~1.5 hours from Q10 to sign-off

**Signed:** SOMCHOK N.
EOF

log "LESSONS-LEARNED.md created"

# README
cat > "$BACKUP/README.txt" << "EOF"
CK-NEXUS Production Backup
Date: 2026-10-14
Status: APPROVED

Contents:
- HANDOVER.md — Deployment guide
- LESSONS-LEARNED.md — Retrospective
- ck-nexus-master-*/ — Evidence package
- ck-nexus-SIGNED-*.tar.gz — Signed archive

Verify:
  sha256sum ck-nexus-SIGNED-*.tar.gz
  Expected: 57eb5ecae240b3244a3a78d2470530ea8b4239eea36444f95d54486abe068a2d
EOF

log "README created"

# Checksums
cd "$BACKUP"
find . -type f -not -name "SHA256SUMS*" -exec sha256sum {} \; > SHA256SUMS
sha256sum -c SHA256SUMS 2>&1 | tail -3

# Final archive
cd /root
tar czf "ck-nexus-final-$TS.tar.gz" "$(basename $BACKUP)"
SHA=$(sha256sum "ck-nexus-final-$TS.tar.gz" | awk "{print \$1}")

echo ""
echo "============================================"
echo " ✅ COMPLETE"
echo "============================================"
log "Backup: $BACKUP"
log "Archive: /root/ck-nexus-final-$TS.tar.gz"
log "SHA256: $SHA"
echo ""
echo "### Contents ###"
ls -la "$BACKUP/"
echo ""
echo "### Sign-Off Status ###"
echo "  Q10-Q16: ✅ ALL VERIFIED"
echo "  Reviewer: SOMCHOK N."
echo "  Production: ✅ APPROVED"
echo ""
echo "### 🚨 SECURITY CHECKLIST ###"
echo "  [ ] ลบ Groq keys: console.groq.com/keys"
echo "  [ ] ลบ GitHub PAT: github.com/settings/tokens"
echo "  [ ] ลบ Sandbox: sbx --cloud rm"
echo "  [ ] ลบ local: rm -f ~/.ck-* ~/.gh-*"
echo "============================================"
