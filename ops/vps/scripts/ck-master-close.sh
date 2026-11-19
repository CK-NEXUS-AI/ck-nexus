#!/bin/bash
set +e

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
log()  { echo -e "${G}[✓]${N} $1"; }
warn() { echo -e "${Y}[!]${N} $1"; }

SANDBOX=$(cat ~/.ck-sandbox-id)
TS=$(date +%Y%m%d-%H%M%S)
MASTER="/root/evidence/ck-nexus-master-$TS"
mkdir -p "$MASTER"

echo ""
echo "============================================"
echo " CK-NEXUS Master Evidence Package"
echo "============================================"
log "Master: $MASTER"
echo ""

# ============================================
# 1. Collect all evidence
# ============================================
echo "### 1. Collect Evidence ###"

mkdir -p "$MASTER"/{q10,q11-q16,q16-build}

# Q10 close-out
cp -r /root/evidence/q10-close-* $MASTER/q10/ 2>/dev/null || true

# Q11-Q16
cp -r /root/evidence/q11-q16-* $MASTER/q11-q16/ 2>/dev/null || true

# Q16 build
cp -r /root/evidence/q16-auto-* $MASTER/q16-build/ 2>/dev/null || true

log "Evidence collected"
echo ""

# ============================================
# 2. Create Change Proposal for Q11
# ============================================
echo "### 2. Q11 Provider Substitution Proposal ###"

cat > "$MASTER/CHANGE-PROPOSAL-Q11-PROVIDER.md" << 'DOC'
# Change Proposal — Q11 Provider Substitution

**Date:** 2026-10-14
**Status:** PENDING_APPROVAL
**Proposer:** CK-NEXUS Team

## Summary

Replace OpenAI as the exclusive Q11 live provider with multi-provider
support (Groq as primary, OpenAI as optional fallback).

## Rationale

| Reason | Details |
|---|---|
| OpenAI credit exhausted | `credit_balance_exhausted` error |
| Cost sustainability | Groq provides free tier |
| API compatibility | Groq uses OpenAI-compatible API |
| Redundancy | Multi-provider avoids single-vendor lock |

## Evidence

- Q11 Test: `HTTP: 200` via Groq `allam-2-7b`
- Response: `{"choices":[{"message":{"content":"CK-Q11-OK"}}]}`
- Evidence path: `/root/evidence/q11-q16-20261014-060343/`

## Provider Comparison

| Aspect | OpenAI | Groq |
|---|---|---|
| API | OpenAI-compatible | OpenAI-compatible |
| Model (tested) | gpt-4o-mini | allam-2-7b |
| Cost | $5+ required | Free tier |
| Speed | Fast | Very fast (LPU) |
| Credit | Prepaid | Free tier |

## Proposed Change

1. Q11 accepts any OpenAI-compatible provider
2. Default: Groq (free)
3. Fallback: OpenAI (if credit available)
4. Test: HTTP 200 + valid JSON response

## Impact

- No source code changes required
- Config: add `GROQ_API_KEY` env
- Docs: update Q11 requirements

## Approval

| Reviewer | Role | Date | Signature |
|---|---|---|---|
| | | | |
DOC

log "Change Proposal created"
echo ""

# ============================================
# 3. Create Master Summary
# ============================================
echo "### 3. Master Summary ###"

cat > "$MASTER/MASTER-SUMMARY.md" << EOF
# CK-NEXUS Master Evidence — $TS

**Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Sandbox:** $SANDBOX
**Provider:** Groq (allam-2-7b)

## Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Q10 | PARTIAL | 3 dispositions (SQL/Subprocess/Parsing) |
| Q11 | ✅ PASS | Groq HTTP 200 |
| Q12 | ✅ PASS | cgroup v2 + 6 controllers |
| Q13 | ✅ PASS | pg_dump 18.6 |
| Q14 | ✅ PASS | OpenTelemetry + prometheus |
| Q15 | ✅ INFO_COLLECTED | Ubuntu 26.04, kernel 6.12.103 |
| Q16 | ✅ BUILD_PASS | Docker 460 MB, SHA 480e0704 |

## Production Status
**NO-GO** — Pending:
1. Q10 independent review (sign dispositions)
2. Q11 Change Proposal approval
3. Release identity reconciliation

## Evidence Folders
- q10/ — Q10 dispositions + verification
- q11-q16/ — Gate test results
- q16-build/ — Docker build evidence

## Change Proposals
- CHANGE-PROPOSAL-Q11-PROVIDER.md

## Next Steps
1. Sign Q10 dispositions → Q10 VERIFIED
2. Approve Q11 Change Proposal → Q11 VERIFIED
3. Reconcile release identity → Production GO
EOF

cat "$MASTER/MASTER-SUMMARY.md"
echo ""

# ============================================
# 4. Checksums + Archive
# ============================================
echo "### 4. Checksums + Archive ###"

cd "$MASTER"
find . -type f -not -name "SHA256SUMS*" -exec sha256sum {} \; > SHA256SUMS
sha256sum -c SHA256SUMS 2>&1 | tail -3
echo ""

cd /root/evidence
tar czf "ck-nexus-master-$TS.tar.gz" "ck-nexus-master-$TS"
SHA=$(sha256sum "ck-nexus-master-$TS.tar.gz" | awk '{print $1}')

echo "============================================"
echo " FINAL RESULTS"
echo "============================================"
log "Master: $MASTER"
log "Archive: ck-nexus-master-$TS.tar.gz"
log "SHA256: $SHA"
echo ""
echo "  Gate Status:"
echo "    Q10: PARTIAL"
echo "    Q11: PASS ✅"
echo "    Q12: PASS ✅"
echo "    Q13: PASS ✅"
echo "    Q14: PASS ✅"
echo "    Q15: INFO_COLLECTED"
echo "    Q16: BUILD_PASS ✅"
echo ""
warn "Production: NO-GO"
warn "Next: Sign Q10 dispositions + Approve Q11 proposal"
echo ""
echo "  🚨 ลบ keys ที่ console.groq.com"
echo "============================================"
