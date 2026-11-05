#!/usr/bin/env bash
set -euo pipefail

VERSION="${TRIVY_VERSION:-0.76.1}"
CHECKSUM_SHA256="885debc41b570179e81af560e5f393a66be29b9ff8c52915674f3eb2304c535d"
DEST="${RUNNER_TEMP:-/tmp}/cknexus-trivy-${VERSION}"
CHECKSUM_FILE="trivy_${VERSION}_checksums.txt"
ARCHIVE="trivy_${VERSION}_Linux-64bit.tar.gz"

mkdir -p "$DEST"
curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${VERSION}/${CHECKSUM_FILE}" -o "$DEST/$CHECKSUM_FILE"
printf '%s  %s\n' "$CHECKSUM_SHA256" "$DEST/$CHECKSUM_FILE" | sha256sum -c -
EXPECTED="$(awk -v name="$ARCHIVE" '$2 == name {print $1}' "$DEST/$CHECKSUM_FILE")"
test "$EXPECTED" = "c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0"
curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${VERSION}/${ARCHIVE}" -o "$DEST/$ARCHIVE"
printf '%s  %s\n' "$EXPECTED" "$DEST/$ARCHIVE" | sha256sum -c -
tar -xzf "$DEST/$ARCHIVE" -C "$DEST" trivy
sudo install -m 0755 "$DEST/trivy" /usr/local/bin/trivy
trivy --version
