#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/spinlnw10-art/ck-nexus}"
RUNNER_TOKEN="${RUNNER_TOKEN:-}"
RUNNER_NAME="${RUNNER_NAME:-q10-linux-$(hostname)}"
RUNNER_LABELS="${RUNNER_LABELS:-q10-linux,linux}"
RUNNER_VERSION="${RUNNER_VERSION:-2.336.0}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/actions-runner-q10}"

if [ -z "$RUNNER_TOKEN" ]; then
  echo 'ERROR: RUNNER_TOKEN is required and must be supplied only through the local environment.' >&2
  exit 20
fi

case "$(uname -m)" in
  x86_64|amd64)
    ARCH=x64
    EXPECTED_SHA256=04cf0be1aff4c3ec3554466c39124ca250e3effd8873bb7e8d68535aa9505d5d
    ;;
  aarch64|arm64)
    ARCH=arm64
    EXPECTED_SHA256=58b758e420b87093fbd4bfddd368074960053e2f1388f01848c82624b90f27d1
    ;;
  *) echo "ERROR: unsupported architecture: $(uname -m)" >&2; exit 21 ;;
esac

command -v curl >/dev/null || { echo 'ERROR: curl missing' >&2; exit 22; }
command -v sha256sum >/dev/null || { echo 'ERROR: sha256sum missing' >&2; exit 23; }
command -v tar >/dev/null || { echo 'ERROR: tar missing' >&2; exit 24; }

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
TARBALL="actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz"
URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"

if [ ! -f "$TARBALL" ]; then
  curl -fL --retry 3 --retry-delay 2 -o "$TARBALL" "$URL"
fi
printf '%s  %s\n' "$EXPECTED_SHA256" "$TARBALL" | sha256sum -c -

tar xzf "$TARBALL"
./config.sh --url "$REPO_URL" --token "$RUNNER_TOKEN" --name "$RUNNER_NAME" --labels "$RUNNER_LABELS" --unattended --replace

cat > q10-runner.env <<EOF
REPO_URL=$REPO_URL
RUNNER_NAME=$RUNNER_NAME
RUNNER_LABELS=$RUNNER_LABELS
RUNNER_VERSION=$RUNNER_VERSION
INSTALL_DIR=$INSTALL_DIR
EOF
chmod 600 q10-runner.env

echo 'Q10_RUNNER=CONFIGURED'
echo "RUNNER_NAME=$RUNNER_NAME"
echo "RUNNER_LABELS=$RUNNER_LABELS"
echo "RUNNER_VERSION=$RUNNER_VERSION"
echo "START_COMMAND=cd $INSTALL_DIR && ./run.sh"
