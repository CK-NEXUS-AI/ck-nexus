#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-/root/ck-nexus-import/pins-470}"
IN="$BASE/incoming"
PROC="$BASE/processed"
MAN="$BASE/manifests"
REP="$BASE/reports"

mkdir -p "$IN" "$PROC" "$MAN" "$REP"
chmod 700 "$BASE" "$IN" "$PROC" "$MAN" "$REP"

find "$IN" -type f -print0 | sort -z | xargs -0 -r sha256sum > "$MAN/sha256-manifest.txt"

awk '{print $1}' "$MAN/sha256-manifest.txt" | sort | uniq -d > "$MAN/duplicate-hashes.txt"
: > "$MAN/duplicate-files.txt"
if [ -s "$MAN/duplicate-hashes.txt" ]; then
  while IFS= read -r hash; do
    grep "^$hash " "$MAN/sha256-manifest.txt" >> "$MAN/duplicate-files.txt" || true
  done < "$MAN/duplicate-hashes.txt"
fi

total=$(find "$IN" -type f | wc -l)
images=$(find "$IN" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.heic' \) | wc -l)
manifest=$(wc -l < "$MAN/sha256-manifest.txt")
dups=$(wc -l < "$MAN/duplicate-hashes.txt")

cat > "$REP/intake-summary.json" <<JSON
{
  "incoming_files": $total,
  "image_files": $images,
  "manifest_lines": $manifest,
  "duplicate_hashes": $dups,
  "state": "$([ "$total" -gt 0 ] && echo READY_FOR_EXTRACTION || echo WAITING_FOR_UPLOAD)"
}
JSON

printf 'incoming_files=%s\n' "$total"
printf 'image_files=%s\n' "$images"
printf 'manifest_lines=%s\n' "$manifest"
printf 'duplicate_hashes=%s\n' "$dups"
printf 'summary=%s\n' "$REP/intake-summary.json"
