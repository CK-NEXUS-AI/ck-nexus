# CK-NEXUS Evidence Signing & Chain-of-Custody V1

Status: DEVELOPMENT / MEASURED_NOT_INDEPENDENTLY_VERIFIED  
Production effect: NONE

## Purpose

V1 binds evidence artifacts to an exact CK-NEXUS subject and preserves a tamper-evident
chain of custody without allowing a system/AI signature to self-promote a release gate.

The implementation reuses the existing `AppendOnlyLedger` hash-chain instead of adding
another ledger or blockchain.

## Exact evidence model

An evidence manifest binds:

- repository;
- exact commit;
- exact tree;
- environment;
- scanner name and version;
- run ID when available;
- artifact relative path;
- artifact SHA-256;
- artifact byte size;
- observation timestamp.

Typical scanner output set:

- `findings.json`
- `coverage.json`
- `report.md`

The generated control artifacts are:

- `scan-manifest.json`
- `chain-of-custody.jsonl`
- `chain-of-custody.json`
- `signature-envelope.json`
- `SHA256SUMS.txt`

## Trust boundary

There are three separate signer roles:

1. `SYSTEM_SIGNER` — cryptographic artifact-integrity/provenance evidence.
2. `HUMAN_REVIEWER` — independent human review.
3. `OWNER_SIGNER` — final owner sign-off.

A valid system cryptographic signature does **not** satisfy either human role.

V1 always emits:

- `release_gate_effect: NONE`
- `production_authorized: false`

Therefore it cannot set Q10/Q11/Q12 PASS and cannot authorize Production.

## CLI

Build an unsigned evidence bundle:

```bash
python -m creator_app.evidence_signing_cli build \
  --root ./scanner-output \
  --repository spinlnw10-art/ck-nexus \
  --commit <exact-commit> \
  --tree <exact-tree> \
  --environment linux-x86_64 \
  --scanner native-scanner \
  --scanner-version <exact-version> \
  --run-id <run-id> \
  --artifact findings.json \
  --artifact coverage.json \
  --artifact report.md \
  --output-dir ./signed-evidence-candidate
```

Verify the manifest hashes and custody chain:

```bash
python -m creator_app.evidence_signing_cli verify \
  --root ./scanner-output \
  --bundle-dir ./signed-evidence-candidate
```

An integrity PASS from this command means only that the artifact hashes and custody chain
match. It does not mean cryptographic signature complete, independent review complete, or
Production certified.

## Sigstore/Cosign integration boundary

The Python adapter supports **verification** of a standardized Sigstore bundle using a
certificate identity and OIDC issuer policy.

It deliberately rejects:

- legacy/non-standard bundle JSON;
- Cosign versions older than 3.1.3 for the keyless bundle verification path.

The minimum version is a security floor for this integration, not a statement that 3.1.3
must remain the latest version forever.

Automated keyless signing is not enabled by this V1 because it can create an external
transparency-log record. That external write needs its own policy/approval decision.

Private signing keys are never generated, stored, printed, committed, or requested by this
module.

## Relation to existing CK-NEXUS evidence

This V1 complements rather than replaces:

- `creator_app/agnes_ledger.py`;
- `creator_app/connector_fabric/evidence.py`;
- `.github/release-tools/verify_release_evidence_provenance.py`;
- `docs/RELEASE_EVIDENCE_PROVENANCE.md`.

GitHub Actions provenance, native Codex Security evidence, Q11 live-provider evidence,
Q12 delegated-runtime evidence, independent HUMAN review, and owner HUMAN sign-off remain
separate mandatory authorities where required.

## Recommended next delta

After V1 is independently reviewed:

1. bind the exact canonical Q10 artifacts to this manifest format;
2. add an explicitly approved Sigstore signing lane;
3. capture the standardized bundle as immutable evidence;
4. verify identity/issuer and bundle against the exact manifest;
5. append the signing event to chain of custody;
6. keep HUMAN_REVIEWER and OWNER_SIGNER fail-closed;
7. benchmark this added layer against the current release-evidence provenance verifier.

No signing layer may weaken or replace an existing Production Closure gate.
