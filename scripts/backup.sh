#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-$ROOT/backups/$STAMP}"
mkdir -p "$DEST"

# Source snapshot excludes secrets, build output, existing backups, and runtime DB files.
tar \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./.env.local' \
  --exclude='./.env.p0' \
  --exclude='./backups' \
  --exclude='./data' \
  --exclude='./build' \
  --exclude='./dist' \
  -czf "$DEST/project-source.tgz" -C "$ROOT" .

python - "$ROOT" "$DEST" <<'PY'
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
root, dest = map(Path, sys.argv[1:])
src = root / 'data' / 'cknexus.db'
if src.exists():
    dst = dest / 'creator.sqlite3'
    with sqlite3.connect(src) as source, sqlite3.connect(dst) as target:
        source.backup(target)
PY

if command -v docker >/dev/null 2>&1 && docker compose -f "$ROOT/docker-compose.p0.yml" ps db --status running >/dev/null 2>&1; then
  docker compose -f "$ROOT/docker-compose.p0.yml" exec -T db \
    pg_dump -U cknexus -d cknexus --format=custom > "$DEST/email-postgres.dump"
else
  printf '%s\n' 'PostgreSQL dump not captured: docker/db unavailable' > "$DEST/POSTGRES_BLOCKED.txt"
fi

(
  cd "$DEST"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
echo "$STAMP" > "$DEST/BACKUP_ID"
echo "Backup created: $DEST"
