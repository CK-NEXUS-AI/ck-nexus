#!/usr/bin/env bash
set -euo pipefail

ROOT="${Q10_EVIDENCE_ROOT:-$PWD/.q10-oneclick/evidence}"
CANONICAL="${Q10_CANONICAL_DIR:-$ROOT/canonical}"
EXTERNAL="${Q10_EXTERNAL_DIR:-$ROOT/external}"
INDEPENDENT="${Q10_INDEPENDENT_DIR:-$ROOT/independent-review}"
DARKER="${Q10_DARKER_EVIDENCE:-$ROOT/darker-verify.json}"
OUT="${Q10_SIGNOFF_STATE:-$ROOT/READY_FOR_OWNER_SIGNOFF.json}"
SUBJECT="39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
TREE="0525195934f703a8becf8a39f6397b2411e0bb2e"

fail(){ printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }

for f in scan-manifest.json findings.json coverage.json report.md; do
  test -s "$CANONICAL/$f" || fail "missing canonical $f"
done

test -d "$EXTERNAL" || fail "missing external evidence directory"
test "$(find "$EXTERNAL" -maxdepth 1 -type f | wc -l | tr -d ' ')" -gt 0 || fail "missing vendor evidence"
test -s "$INDEPENDENT/attestation.json" || fail "missing independent attestation"
test -s "$DARKER" || fail "missing Darker verification evidence"

grep -Eq '"valid"[[:space:]]*:[[:space:]]*true' "$DARKER" || fail "Darker not valid"
grep -Eq '"verdict"[[:space:]]*:[[:space:]]*"PASS"' "$INDEPENDENT/attestation.json" || fail "independent verdict not PASS"
grep -Eq '"independent"[[:space:]]*:[[:space:]]*true' "$INDEPENDENT/attestation.json" || fail "review independence not attested"

mkdir -p "$(dirname "$OUT")"
HASHES="$(sha256sum "$CANONICAL/scan-manifest.json" "$CANONICAL/findings.json" "$CANONICAL/coverage.json" "$CANONICAL/report.md" "$DARKER" "$INDEPENDENT/attestation.json")"
printf '{"state":"READY_FOR_OWNER_SIGNOFF","subject":"%s","tree":"%s","owner_signed":false}\n' "$SUBJECT" "$TREE" > "$OUT"
printf '%s\n' "$HASHES" > "${OUT%.json}.sha256"
printf 'READY_FOR_OWNER_SIGNOFF\n'
