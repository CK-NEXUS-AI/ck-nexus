#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <release-artifact>" >&2
  exit 64
fi

ARTIFACT="$(realpath "$1")"
test -f "$ARTIFACT"

KEY="${CK_RELEASE_COSIGN_KEY:-/var/lib/ck-nexus-release-signing/ck-nexus-release.pem}"
PUB="${CK_RELEASE_COSIGN_PUB:-$(git rev-parse --show-toplevel)/security/release-signing.pub.pem}"
BUNDLE="${ARTIFACT}.sigstore.json"
CHECKSUM="${ARTIFACT}.sha256"

test -f "$KEY" || { echo "private signing key not found" >&2; exit 2; }
test -f "$PUB" || { echo "public verification key not found" >&2; exit 2; }

mode="$(stat -c %a "$KEY")"
case "$mode" in
  600|400) ;;
  *) echo "refusing to use private key with mode $mode; require 600 or 400" >&2; exit 3 ;;
esac

sha256sum "$ARTIFACT" > "$CHECKSUM"

echo "Cosign may require the authorized human operator to review third-party hosted-service terms."
echo "No terms are accepted automatically by this script."

cosign sign-blob   --key "$KEY"   --bundle "$BUNDLE"   "$ARTIFACT"

cosign verify-blob   --key "$PUB"   --bundle "$BUNDLE"   "$ARTIFACT"

echo "signed_artifact=$ARTIFACT"
echo "bundle=$BUNDLE"
echo "checksum=$CHECKSUM"
