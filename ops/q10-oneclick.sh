#!/usr/bin/env bash
set -euo pipefail

SUBJECT="39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
TREE="0525195934f703a8becf8a39f6397b2411e0bb2e"
ROOT="${Q10_ROOT:-$PWD/.q10-oneclick}"
SRC="$ROOT/frozen-source"
EVD="$ROOT/evidence"
STATE="$ROOT/state.json"
mkdir -p "$EVD"

now(){ date -u +%Y-%m-%dT%H:%M:%SZ; }
write_state(){ printf '{"state":"%s","subject":"%s","tree":"%s","updated_at":"%s"}\n' "$1" "$SUBJECT" "$TREE" "$(now)" > "$STATE"; }
fail(){ write_state "BLOCKED"; printf '%s\n' "$*" >&2; exit 1; }

write_state "PREFLIGHT"
command -v git >/dev/null || fail "git missing"

if [ ! -d "$SRC/.git" ]; then
  git clone --no-checkout "${Q10_REPO_URL:-https://github.com/spinlnw10-art/ck-nexus.git}" "$SRC"
fi
git -C "$SRC" fetch --quiet origin "$SUBJECT"
git -C "$SRC" checkout --detach --force "$SUBJECT"
actual_subject="$(git -C "$SRC" rev-parse HEAD)"
actual_tree="$(git -C "$SRC" rev-parse 'HEAD^{tree}')"
[ "$actual_subject" = "$SUBJECT" ] || fail "subject mismatch"
[ "$actual_tree" = "$TREE" ] || fail "tree mismatch"
[ -z "$(git -C "$SRC" status --porcelain)" ] || fail "frozen source dirty"
printf 'subject=%s\ntree=%s\nverified_at=%s\n' "$actual_subject" "$actual_tree" "$(now)" > "$EVD/subject-binding.txt"

write_state "STATIC_SCANS"
scan_fail=0
if command -v semgrep >/dev/null; then
  (cd "$SRC" && semgrep scan --config auto --json --output "$EVD/semgrep.json" .) || scan_fail=1
else
  printf '{"status":"BLOCKED","reason":"semgrep_missing"}\n' > "$EVD/semgrep.json"
  scan_fail=1
fi
if command -v trivy >/dev/null; then
  trivy fs --scanners vuln,misconfig,secret --format json --output "$EVD/trivy.json" "$SRC" || scan_fail=1
else
  printf '{"status":"BLOCKED","reason":"trivy_missing"}\n' > "$EVD/trivy.json"
  scan_fail=1
fi

write_state "ARTIFACT_GATE"
sha256sum "$EVD/subject-binding.txt" "$EVD/semgrep.json" "$EVD/trivy.json" > "$EVD/SHA256SUMS"

# External/vendor evidence is optional for execution but mandatory for closure.
# Drop/export Aikido evidence into $EVD/external/ before final closure.
mkdir -p "$EVD/external"
external_count="$(find "$EVD/external" -maxdepth 1 -type f | wc -l | tr -d ' ')"

# Canonical Codex deep-scan artifacts remain mandatory for Q10 closure.
canonical_dir="${Q10_CANONICAL_DIR:-$EVD/canonical}"
canonical_ok=1
for f in scan-manifest.json findings.json coverage.json report.md; do
  [ -s "$canonical_dir/$f" ] || canonical_ok=0
done

if [ "$scan_fail" -ne 0 ]; then
  fail "static scan lane incomplete"
fi
if [ "$external_count" -lt 1 ]; then
  write_state "WAITING_EXTERNAL_EVIDENCE"
  printf 'Static scans complete; waiting for independent/vendor evidence.\n'
  exit 2
fi
if [ "$canonical_ok" -ne 1 ]; then
  write_state "WAITING_CANONICAL_Q10"
  printf 'Independent evidence present; waiting for canonical Q10 deep-scan artifacts.\n'
  exit 3
fi

sha256sum "$canonical_dir"/scan-manifest.json "$canonical_dir"/findings.json "$canonical_dir"/coverage.json "$canonical_dir"/report.md >> "$EVD/SHA256SUMS"
write_state "READY_FOR_INDEPENDENT_REVIEW"
printf 'Q10 evidence lanes complete. Independent reviewer attestation and owner sign-off are still required.\n'
