#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/security-evidence-delta}"
mkdir -p "$OUT"
cd "$ROOT"
status=0

run_or_block() {
  local name="$1"; shift
  if command -v "$1" >/dev/null 2>&1; then
    echo "[RUN] $name"
    "$@" || status=1
  else
    echo "[BLOCKED] $name: $1 not installed" | tee "$OUT/${name}.blocked.txt"
    [[ "$status" -eq 1 ]] || status=2
  fi
}

if command -v osv-scanner >/dev/null 2>&1; then
  osv-scanner scan source --recursive --format json --output-file "$OUT/osv-results.json" . || status=1
else
  echo '[BLOCKED] osv-scanner not installed' | tee "$OUT/osv.blocked.txt"
  status=2
fi

if command -v checkov >/dev/null 2>&1; then
  checkov -d . --framework dockerfile github_actions --output json > "$OUT/checkov-results.json" || status=1
else
  echo '[BLOCKED] checkov not installed' | tee "$OUT/checkov.blocked.txt"
  [[ "$status" -eq 1 ]] || status=2
fi

printf '{"lane":"security-evidence-delta","status":%d,"subject":"%s","tree":"%s"}\n' \
  "$status" "$(git rev-parse HEAD)" "$(git rev-parse HEAD^{tree})" > "$OUT/manifest.json"
exit "$status"
