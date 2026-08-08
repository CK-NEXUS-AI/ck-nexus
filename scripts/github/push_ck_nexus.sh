#!/usr/bin/env bash
set -euo pipefail
OWNER="${GITHUB_OWNER:-spinlnw10-art}"
REPO="${GITHUB_REPO_NAME:-ck-nexus}"
TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  echo "BLOCKED: set GITHUB_TOKEN in the environment (do not paste it into source or shell history)." >&2
  exit 2
fi
REMOTE="https://github.com/${OWNER}/${REPO}.git"
ASKPASS="$(mktemp)"
trap 'rm -f "$ASKPASS"' EXIT
cat > "$ASKPASS" <<'EOF'
#!/usr/bin/env sh
case "$1" in
  *Username*) printf '%s\n' "${GITHUB_OWNER:-spinlnw10-art}" ;;
  *Password*) printf '%s\n' "$GITHUB_TOKEN" ;;
  *) printf '\n' ;;
esac
EOF
chmod 700 "$ASKPASS"
export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi
# Token is never embedded in the remote URL.
git push -u origin main
git push origin v0.2.0-p0-rc
printf 'PUSHED %s at %s\n' "$REMOTE" "$(git rev-parse HEAD)"
