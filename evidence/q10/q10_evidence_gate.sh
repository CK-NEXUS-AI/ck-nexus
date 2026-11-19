#!/usr/bin/env bash
# =============================================================================
# Q10 EVIDENCE GATE — Working Automation (adapted from "conversation → system")
# =============================================================================
# Concept: Noah Epstein's n8n post — "no code, no templates, just a conversation"
# Adapted: describe the gate → this script RUNS the whole evidence gate.
# "คิดได้ทุกทำได้" — whatever you think of, the system executes it.
#
# USAGE:  bash q10_evidence_gate.sh /path/to/ck-nexus-repo [--skip-install]
# SAFETY: read-only scans only. No exfiltration. No destructive ops. Non-root OK.
# =============================================================================
set -euo pipefail

# --- SAFETY GUARD: refuse to run as root (least privilege) ---
if [ "$(id -u)" -eq 0 ]; then
  echo "REFUSED: do not run as root. Use a non-root user (least privilege)." >&2
  exit 1
fi

REPO="${1:?Usage: bash q10_evidence_gate.sh /path/to/repo [--skip-install]}"
SKIP_INSTALL="${2:-}"
OUT_DIR="${Q10_OUT_DIR:-/tmp/q10-evidence-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT_DIR"

echo "=== Q10 EVIDENCE GATE ==="
echo "Repo: $REPO"
echo "Output: $OUT_DIR"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- STEP 0: Freeze HEAD (commit freezer) -------------------------------
cd "$REPO"
HEAD_SHA=$(git rev-parse HEAD)
TREE_HASH=$(git rev-parse 'HEAD^{tree}')
echo "HEAD_SHA=$HEAD_SHA"
echo "TREE_HASH=$TREE_HASH"
git status --porcelain > "$OUT_DIR/git_status_porcelain.txt" || true
git diff --name-status HEAD~1..HEAD > "$OUT_DIR/git_diff_last_commit.txt" 2>/dev/null || true

# --- STEP 1: Install tools non-root (pipx) ------------------------------
if [ "$SKIP_INSTALL" != "--skip-install" ]; then
  echo "--- Installing tools (non-root, pipx) ---"
  command -v pipx >/dev/null 2>&1 || pip3 install --user pipx
  export PATH="$HOME/.local/bin:$PATH"
  pipx ensurepath >/dev/null 2>&1 || true
  for tool in pip-audit semgrep gitleaks; do
    command -v "$tool" >/dev/null 2>&1 || pipx install "$tool" || echo "WARN: could not install $tool"
  done
  command -v trivy >/dev/null 2>&1 || echo "WARN: trivy not installed (install via https://github.com/aquasecurity/trivy)"
  command -v osv-scanner >/dev/null 2>&1 || echo "WARN: osv-scanner not installed"
fi
export PATH="$HOME/.local/bin:$PATH"

# --- STEP 2: EG-1 SCA (Dependency) --------------------------------------
echo "--- EG-1: SCA (pip-audit) ---"
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit -r requirements.txt --format json > "$OUT_DIR/eg1_pip_audit.json" 2>"$OUT_DIR/eg1_pip_audit.err" \
    && echo "EG1 pip-audit: OK" || echo "EG1 pip-audit: FAILED (see err)"
fi
if command -v trivy >/dev/null 2>&1; then
  trivy fs --scanners vuln --format json -o "$OUT_DIR/eg1_trivy_vuln.json" . >/dev/null 2>&1 \
    && echo "EG1 trivy: OK" || echo "EG1 trivy: FAILED"
fi

# --- STEP 3: EG-2 SAST (Static Code) -------------------------------------
echo "--- EG-2: SAST (Semgrep CE) ---"
if command -v semgrep >/dev/null 2>&1; then
  semgrep scan --config auto --json --output "$OUT_DIR/eg2_semgrep.json" . >/dev/null 2>"$OUT_DIR/eg2_semgrep.err" \
    && echo "EG2 semgrep: OK" || echo "EG2 semgrep: FAILED (see err)"
fi

# --- STEP 4: EG-3 Secret Detection ---------------------------------------
echo "--- EG-3: Secret (gitleaks) ---"
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --source . --report-format json --report-path "$OUT_DIR/eg3_gitleaks.json" --no-banner >/dev/null 2>&1 \
    && echo "EG3 gitleaks: OK" || echo "EG3 gitleaks: FAILED"
fi

# --- STEP 5: EG-4 Config/IaC ---------------------------------------------
echo "--- EG-4: Config/IaC (trivy config) ---"
if command -v trivy >/dev/null 2>&1; then
  trivy config --format json --output "$OUT_DIR/eg4_trivy_config.json" . >/dev/null 2>&1 \
    && echo "EG4 trivy config: OK" || echo "EG4 trivy config: FAILED"
fi

# --- STEP 6: Evidence Bundle + SHA256 ------------------------------------
echo "--- Building evidence bundle ---"
MANIFEST="$OUT_DIR/evidence_manifest.json"
{
  echo "{"
  echo "  \"gate\": \"Q10-PARTIAL\","
  echo "  \"head_sha\": \"$HEAD_SHA\","
  echo "  \"tree_hash\": \"$TREE_HASH\","
  echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"operator\": \"SOMCHOK N.\","
  echo "  \"layers\": {"
  FIRST=1
  for f in "$OUT_DIR"/eg*.json; do
    [ -f "$f" ] || continue
    NAME=$(basename "$f")
    SHA=$(sha256sum "$f" | awk '{print $1}')
    [ $FIRST -eq 0 ] && echo ","
    echo "    \"$NAME\": {\"sha256\": \"$SHA\", \"bytes\": $(stat -c%s "$f")}"
    FIRST=0
  done
  echo ""
  echo "  },"
  echo "  \"eg5_codex\": \"BLOCKED (research preview, not free)\","
  echo "  \"verdict\": \"PARTIAL_CLOSE_PENDING_REVIEW — EG-1..EG-4 evidence collected; EG-5 blocked\""
  echo "}"
} > "$MANIFEST"

echo "--- EG-5: LLM Deep Scan (Codex Security) ---"
echo "EG-5 = BLOCKED (research preview, not free). Not run. Recorded in manifest."

echo ""
echo "=== DONE ==="
echo "Evidence bundle: $OUT_DIR"
echo "Manifest: $MANIFEST"
echo "Next: human review + attest → PARTIAL CLOSE or BLOCKED"