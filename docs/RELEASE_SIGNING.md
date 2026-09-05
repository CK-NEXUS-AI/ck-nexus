# CK-NEXUS Release Signing

## Purpose

Release signing provides artifact integrity and signer authenticity. A valid signature does **not** by itself certify security, compliance, Q10/Q11/Q12 verification, or production readiness.

## Key handling

- Keep the private Cosign key outside the repository.
- Store it with owner-only filesystem permissions or an approved secret manager.
- Commit/publish only the public key.
- Keep the key password outside source control and logs.
- Rotate the key after suspected exposure and document the rotation.
- Never reuse the CK-NEXUS machine-attestation key as the release-signing key.

## Signing

Cosign v3 uses Sigstore bundles as the preferred verification material.

```bash
COSIGN_PRIVATE_KEY=/secure/path/ck-nexus-release.key \
COSIGN_PASSWORD_FILE=/secure/path/ck-nexus-release.password \
scripts/release-signing/sign_blob.sh dist/artifact.tar.gz
```

The helper creates:

- `artifact.tar.gz.sigstore.json`
- `artifact.tar.gz.sha256`
- `artifact.tar.gz.signing-metadata.txt`

## Verification

```bash
scripts/release-signing/verify_blob.sh \
  dist/artifact.tar.gz \
  dist/artifact.tar.gz.sigstore.json \
  security/ck-nexus-release.pub
```

Release evidence should include the artifact SHA-256, Sigstore bundle, public-key fingerprint, source commit/tree, CI run ID, tool version, and timestamp.

## Enforcement status

This procedure is **prepared but not yet a production enforcement gate**. Enabling mandatory signed releases requires human review and explicit adoption.
