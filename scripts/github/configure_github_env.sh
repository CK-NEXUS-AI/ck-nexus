#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-/etc/cknexus/cknexus.env}"
mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"

printf 'GitHub repository (owner/name): '
read -r GITHUB_REPO_VALUE
if [ -z "$GITHUB_REPO_VALUE" ] || [[ "$GITHUB_REPO_VALUE" != */* ]]; then
  echo 'ERROR: repository must be owner/name' >&2
  exit 1
fi
printf 'GitHub token (hidden; use a NEW fine-grained PAT or runtime token): '
read -r -s GITHUB_TOKEN_VALUE
printf '\n'
if [ -z "$GITHUB_TOKEN_VALUE" ]; then
  echo 'ERROR: token is empty' >&2
  exit 1
fi

python3 - "$ENV_FILE" "$GITHUB_REPO_VALUE" "$GITHUB_TOKEN_VALUE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
repo = sys.argv[2]
token = sys.argv[3]
current = path.read_text(encoding='utf-8') if path.exists() else ''
lines = [line for line in current.splitlines() if not line.startswith(('GITHUB_TOKEN=', 'GITHUB_REPO=', 'GITHUB_API_BASE='))]
lines += [f'GITHUB_TOKEN={token}', f'GITHUB_REPO={repo}', 'GITHUB_API_BASE=https://api.github.com']
path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
PY
chmod 600 "$ENV_FILE"
unset GITHUB_TOKEN_VALUE

echo "GitHub runtime settings written to: $ENV_FILE"
echo "Token value was not printed. Start CK-NEXUS with this env file, then use SYSTEM -> TEST GITHUB."
