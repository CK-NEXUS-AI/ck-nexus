# CK-NEXUS Release Signing Procedure

## Status

This procedure is prepared but is **not yet an enforced production release gate**.

The repository public verification key is:

`security/release-signing.pub.pem`

Its SHA-256 at preparation time is:

`0bbbb9580961543f58596579a702c3d1edd87f3071adfe6e885bcd5a9d506dfb`

The private signing key is stored outside the repository on the controlled VPS with root-only permissions. It must never be committed, copied into CI logs, attached to an issue, or included in an evidence bundle.

## Intended release flow

1. Produce the release artifact from an exact reviewed commit.
2. Record commit SHA, tree SHA, tool versions, and artifact SHA-256.
3. Run the required tests and security gates.
4. Have an authorized human initiate signing.
5. Create a Cosign verification bundle for the artifact.
6. Verify the bundle with the repository public key.
7. Publish the artifact, bundle, checksums, and public verification key.
8. Preserve all evidence with timestamps and hashes.

## Signing

Run:

```bash
scripts/release/sign-release-artifact.sh path/to/artifact
```

The script intentionally does **not** auto-accept third-party terms. Cosign v3 may require interaction with Sigstore hosted services and may present terms governing public transparency-log submission. The authorized human operator must review and accept any applicable terms directly.

## Verification

After a bundle is produced:

```bash
cosign verify-blob \
  --key security/release-signing.pub.pem \
  --bundle path/to/artifact.sigstore.json \
  path/to/artifact
```

Also verify the artifact checksum independently:

```bash
sha256sum path/to/artifact
```

## Internal machine seal

CK-NEXUS also maintains a local machine-attestation seal for evidence-manifest integrity. That seal is separate from release signing and is **not** an external certification, accreditation, or independent attestation.

## Production boundary

A valid signature proves artifact integrity and signer possession of the signing key. It does not by itself prove software security, compliance, Q10/Q11/Q12 verification, or production readiness.
