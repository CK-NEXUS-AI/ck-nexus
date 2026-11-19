#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_KEY="${1:-spinlnw10-art_ck-nexus-pro-evolution}"
HOST_URL="${SONAR_HOST_URL:-https://sonarcloud.io}"
OUT_ROOT="${SONAR_REPORT_ROOT:-.sonar-reports}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$OUT_ROOT/$PROJECT_KEY/$TS"

if [[ -z "${SONAR_TOKEN:-}" ]]; then
  echo "BLOCKED_CONFIGURATION: SONAR_TOKEN is required via environment only."
  exit 10
fi

mkdir -p "$OUT"
chmod 0700 "$OUT"

HEAD="$(git rev-parse HEAD)"
TREE="$(git rev-parse HEAD^{tree})"
DIRTY="$(git status --porcelain | wc -l)"

{
  echo "project_key=$PROJECT_KEY"
  echo "commit=$HEAD"
  echo "tree=$TREE"
  echo "dirty=$DIRTY"
  echo "started_utc=$TS"
} > "$OUT/run-metadata.txt"

if [[ "$DIRTY" != "0" && "${ALLOW_DIRTY_SONAR_SCAN:-0}" != "1" ]]; then
  echo "BLOCKED: worktree is dirty; refusing non-reproducible analysis."
  exit 11
fi

SCANNER_ARGS=(
  "-Dsonar.host.url=$HOST_URL"
  "-Dsonar.organization=spinlnw10-art"
  "-Dsonar.projectKey=$PROJECT_KEY"
  "-Dsonar.scm.provider=git"
  "-Dsonar.qualitygate.wait=true"
  "-Dsonar.qualitygate.timeout=300"
)

set +e
sonar-scanner "${SCANNER_ARGS[@]}" 2>&1 | tee "$OUT/sonar-scanner.log"
SCAN_RC=${PIPESTATUS[0]}
set -e

echo "scan_exit_code=$SCAN_RC" >> "$OUT/run-metadata.txt"

set +e
python3 scripts/sonar/collect_quality_report.py   --project-key "$PROJECT_KEY"   --host-url "$HOST_URL"   --output-dir "$OUT"   --commit "$HEAD"
REPORT_RC=$?
set -e

echo "report_exit_code=$REPORT_RC" >> "$OUT/run-metadata.txt"

python3 scripts/sonar/verify_reports_no_secrets.py "$OUT"

(
  cd "$OUT"
  find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt
)

if [[ "$SCAN_RC" -ne 0 ]]; then
  exit "$SCAN_RC"
fi
exit "$REPORT_RC"
