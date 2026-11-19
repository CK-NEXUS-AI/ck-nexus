#!/usr/bin/env bash
set -u
LOG="/root/cknexus-final-target-audit-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOG") 2>&1

A='/root/.openclaw/tmp/plugin-captures/e27d427a-9d59-4b15-bdb0-f8db4bd213e0/native/admission-5i9Uoo/content/vendor/x86_64-unknown-linux-musl/bin/codex'
B='/root/.openclaw/npm/projects/openclaw-codex-8902d781d4/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex'
DB='/root/.openclaw/tmp/plugin-captures/e27d427a-9d59-4b15-bdb0-f8db4bd213e0/owner.sqlite'

echo "=== DISK BEFORE ==="
df -hT /

echo
echo "=== CODEX FILE IDENTITY ==="
for f in "$A" "$B"; do
  if [ -f "$f" ]; then
    stat -c 'path=%n size=%s bytes inode=%i modified=%y' "$f"
    sha256sum "$f"
  else
    echo "Missing: $f"
  fi
done
if [ -f "$A" ] && [ -f "$B" ]; then
  if cmp -s "$A" "$B"; then
    echo "IDENTICAL_CONTENT=yes"
  else
    echo "IDENTICAL_CONTENT=no"
  fi
fi

echo
echo "=== CAPTURE OWNER DATABASE ==="
if [ -f "$DB" ]; then
  stat -c '%n %s bytes modified=%y' "$DB"
  command -v lsof >/dev/null 2>&1 && lsof "$DB" || true
  command -v fuser >/dev/null 2>&1 && fuser -v "$DB" 2>&1 || true
fi

echo
echo "=== SANDBOX CLI HELP ==="
sbx --help 2>&1 | head -100
echo
echo "=== SANDBOX LIST ==="
sbx ls 2>&1 || true

echo
echo "=== SNAP APPLICATION DEPENDENCIES ==="
for p in firefox gnome-42-2204 gnome-46-2404 mesa-2404; do
  echo "--- $p ---"
  snap connections "$p" 2>/dev/null || true
done

echo
echo "=== DISK AFTER (AUDIT ONLY) ==="
df -hT /
echo "Report: $LOG"
