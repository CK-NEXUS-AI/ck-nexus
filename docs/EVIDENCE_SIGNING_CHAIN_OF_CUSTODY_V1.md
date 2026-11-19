# CK-NEXUS Evidence Signing & Chain-of-Custody V1

Status: **DEVELOPMENT / CRYPTOGRAPHIC SIGNING CAPABILITY IMPLEMENTED / NOT INDEPENDENTLY VERIFIED**

Production effect: **NONE**  
Q10 effect: **NONE — Q10 remains NOT_VERIFIED**  
Independent human review: **REQUIRED**  
Owner sign-off: **REQUIRED**

## Purpose

This slice adds the missing evidence-integrity layer without rebuilding CK-NEXUS governance,
audit, provenance, CI/CD, or security scanning foundations that already exist.

The signing target is one deterministic manifest:

`evidence-signing-manifest.json`

That manifest binds the exact hashes of the canonical evidence files:

- `scan-manifest.json`
- `findings.json`
- `coverage.json`
- `report.md`

The signed manifest is separate from the verification-state document so that cryptographic signing
can never silently promote human review, owner sign-off, Q10, or Production state.

## Generated bundle

A successful `build` creates:

```text
evidence-signing-manifest.json
SHA256SUMS.txt
chain-of-custody.json
verification-state.json
```

The manifest binds:

- repository identity;
- exact Git commit;
- exact Git tree;
- scanner name/version;
- run identity;
- observed timestamp;
- SHA-256 and byte size for every required artifact.

The custody chain is hash-linked and starts from an all-zero genesis hash. Any edited event,
reordered event, changed artifact, or changed manifest is detected by verification.

## Signer separation

`verification-state.json` deliberately separates three authorities:

```text
SYSTEM SIGNATURE
    -> cryptographic integrity only

INDEPENDENT HUMAN REVIEW
    -> separate PENDING/approved authority

OWNER SIGN-OFF
    -> separate PENDING/approved authority
```

A valid system signature results in:

```text
system_signature = CRYPTOGRAPHICALLY_VERIFIED
independent_human_review = PENDING
owner_signoff = PENDING
Q10 = NOT_VERIFIED
Production = NO-GO
```

This is a fail-closed invariant.

## Sigstore / Cosign integration

`creator_app.evidence_signing.cosign.sign_and_verify_keyless()` supports the current
Cosign blob workflow:

```text
cosign sign-blob --yes --bundle <bundle> <manifest>
cosign verify-blob <manifest> --bundle <bundle> \
  --certificate-identity <expected-identity> \
  --certificate-oidc-issuer <expected-issuer>
```

Keyless signing is intentionally blocked unless the caller explicitly enables
`allow_public_transparency_log`.

Reason: keyless Sigstore signing associates the signing identity with the artifact digest and
publishes auditable signing evidence through Sigstore transparency infrastructure. That external
write is not performed by default for a private CK-NEXUS repository.

## CLI

Build:

```bash
python scripts/evidence_signing_v1.py build \
  --evidence-dir /path/to/evidence \
  --output-dir /path/to/signing \
  --repository spinlnw10-art/ck-nexus \
  --subject-commit <40-char-commit> \
  --subject-tree <40-char-tree> \
  --scanner codex-security \
  --scanner-version <version> \
  --run-id <run-id>
```

Verify:

```bash
python scripts/evidence_signing_v1.py verify \
  --evidence-dir /path/to/evidence \
  --output-dir /path/to/signing
```

Keyless signing is a separate, explicitly authorized operation:

```bash
python scripts/evidence_signing_v1.py sign-sigstore \
  --output-dir /path/to/signing \
  --signer-identity <expected OIDC identity> \
  --oidc-issuer https://token.actions.githubusercontent.com \
  --allow-public-transparency-log
```

Do not run this step merely to make Q10 look complete. A system signature is not an independent
human review and is not certification.

## Existing CK-NEXUS components reused

This V1 reuses rather than replaces:

- release evidence provenance verification;
- council authority;
- Credential Broker boundaries;
- hash-chained audit records;
- existing security gates;
- trusted verifier image provenance.

No new blockchain or parallel audit database is introduced.

## Supply-chain next step

The V1 manifest is intentionally structured so it can later be represented as an in-toto
Statement with SLSA provenance. That is a follow-on delta, not a prerequisite for this V1.

The future attestation must preserve the same exact subject identity and must not reinterpret
cryptographic provenance as certification.

## Definition of done for this development slice

- all four required evidence artifacts are mandatory;
- artifact tampering fails verification;
- custody-chain tampering fails verification;
- invalid Git subject identity fails closed;
- keyless signing requires explicit transparency-log authorization;
- a verified system signature cannot change human/owner/Q10/Production state;
- targeted CI and security regression pass on the exact candidate head.

Independent human review remains outside this implementation.

## Internal offline Ed25519 signing

For private/internal evidence where CK-NEXUS must not publish signing metadata to an external
transparency service, V1 also supports an OpenSSL Ed25519 path:

```bash
python scripts/evidence_signing_v1.py sign-ed25519 \
  --output-dir /path/to/signing \
  --private-key /secure/path/internal-signing-key.pem \
  --public-key /secure/path/internal-signing-key.pub.pem
```

The private key is never written into the evidence bundle and must remain outside the evidence
directory with restrictive filesystem permissions. The signer identity stored in
`verification-state.json` is the SHA-256 fingerprint of the public-key file.

This is an **internal cryptographic system signature only**. It does not create an accredited
certificate, independent human review, owner sign-off, Q10 PASS, or Production authorization.
