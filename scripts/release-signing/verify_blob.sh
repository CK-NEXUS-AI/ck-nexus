#!/usr/bin/env bash
set -euo pipefail

artifact="${1:?usage: verify_blob.sh <artifact> <bundle> <public-key>}"
bundle="${2:?missing sigstore bundle}"
public_key="${3:?missing public key}"

test -f "$artifact"
test -f "$bundle"
test -f "$public_key"

cosign verify-blob   --key "$public_key"   --bundle "$bundle"   "$artifact"

if [ -f "$artifact.sha256" ]; then
  sha256sum -c "$artifact.sha256"
fi
