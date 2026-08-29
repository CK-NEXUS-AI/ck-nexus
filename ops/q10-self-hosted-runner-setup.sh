#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/spinlnw10-art/ck-nexus}"
RUNNER_TOKEN="${RUNNER_TOKEN:-}"
RUNNER_NAME="${RUNNER_NAME:-q10-linux-$(hostname)}"
RUNNER_LABELS="${RUNNER_LABELS:-q10-linux,linux}"
RUNNER_VERSION="${RUNNER_VERSION:-2.329.0}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/actions-runner-q10}"

if [ -z "$RUNNER_TOKEN" ]; then
  echo 'ERROR: RUNNER_TOKEN is required. Get it from GitHub repo Settings > Actions > Runners > New self-hosted runner.' >&2
  exit 20
fi

case "$(uname -m)" in
  x86_64|amd64) ARCH=x64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "ERROR: unsupported architecture: $(uname -m)" >&2; exit 21 ;;
esac

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

TARBALL="actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz"
URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

if [ ! -f "$TARBALL" ]; then
  curl -fL --retry 3 --retry-delay 2 -o "$TARBALL" "$URL"
fi

tar xzf "$TARBALL"

./config.sh \
  --url "$REPO_URL" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --unattended \
  --replace

cat > q10-runner.env <<EOF
REPO_URL=$REPO_URL
RUNNER_NAME=$RUNNER_NAME
RUNNER_LABELS=$RUNNER_LABELS
INSTALL_DIR=$INSTALL_DIR
EOF

echo 'Runner configured. Start it with:'
echo "cd $INSTALL_DIR && ./run.sh"
echo 'For service install on systemd Linux, run ./svc.sh install && ./svc.sh start after review.'
