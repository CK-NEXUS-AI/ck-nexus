#!/usr/bin/env bash
set -euo pipefail

artifact="${1:?usage: sign_blob.sh <artifact>}"
key="${COSIGN_PRIVATE_KEY:?COSIGN_PRIVATE_KEY must point to the private Cosign key}"
password_file="${COSIGN_PASSWORD_FILE:?COSIGN_PASSWORD_FILE must point to a root/owner-only password file}"
bundle="${artifact}.sigstore.json"

test -f "$artifact"
test -f "$key"
test -f "$password_file"

export COSIGN_PASSWORD
COSIGN_PASSWORD="$(cat "$password_file")"

cosign sign-blob   --yes   --key "$key"   --bundle "$bundle"   "$artifact"

sha256sum "$artifact" > "$artifact.sha256"
printf 'signed_utc=%s\n' "$(date -u +%FT%TZ)" > "$artifact.signing-metadata.txt"
cosign version >> "$artifact.signing-metadata.txt"
